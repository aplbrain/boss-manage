"""
Create the production configuration which consists of
  * An endpoint web server in the external subnet
  * A RDS DB Instance launched into two new subnets (A and B)

The production configuration creates all of the resources needed to run the
BOSS system. The production configuration expects to be launched / created
in a VPC created by the core configuration. It also expects for the user to
select the same KeyPair used when creating the core configuration.
"""


import configuration
import library as lib
import hosts
import json
import scalyr
import uuid

# Region production is created in.  Later versions of boto3 should allow us to
# extract this from the session variable.  Hard coding for now.
PRODUCTION_REGION = 'us-east-1'

DYNAMO_SCHEMA = '../salt_stack/salt/boss/files/boss.git/django/bosscore/dynamo_schema.json'

INCOMING_SUBNET = "52.3.13.189/32" # microns-bastion elastic IP

VAULT_DJANGO = "secret/endpoint/django"
VAULT_DJANGO_DB = "secret/endpoint/django/db"
VAULT_DJANGO_AUTH = "secret/endpoint/auth"

def create_config(session, domain, keypair=None, user_data=None, db_config={}):
    """Create the CloudFormationConfiguration object."""
    config = configuration.CloudFormationConfiguration(domain, PRODUCTION_REGION)

    # do a couple of verification checks
    if config.subnet_domain is not None:
        raise Exception("Invalid VPC domain name")

    vpc_id = lib.vpc_id_lookup(session, domain)
    if session is not None and vpc_id is None:
        raise Exception("VPC does not exists, exiting...")

    # Lookup the VPC, External Subnet, Internal Security Group IDs that are
    # needed by other resources
    config.add_arg(configuration.Arg.VPC("VPC", vpc_id,
                                         "ID of VPC to create resources in"))

    external_subnet_id = lib.subnet_id_lookup(session, "external." + domain)
    config.add_arg(configuration.Arg.Subnet("ExternalSubnet",
                                            external_subnet_id,
                                            "ID of External Subnet to create resources in"))

    internal_sg_id = lib.sg_lookup(session, vpc_id, "internal." + domain)
    config.add_arg(configuration.Arg.SecurityGroup("InternalSecurityGroup",
                                                   internal_sg_id,
                                                   "ID of internal Security Group"))

    az_subnets = config.find_all_availability_zones(session)

    config.add_ec2_instance("Endpoint",
                            "endpoint." + domain,
                            lib.ami_lookup(session, "endpoint.boss"),
                            keypair,
                            public_ip = True,
                            subnet = "ExternalSubnet",
                            security_groups = ["InternalSecurityGroup", "InternetSecurityGroup"],
                            user_data = user_data,
                            depends_on = "EndpointDB") # make sure the DB is launched before we start

    config.add_rds_db("EndpointDB",
                      "endpoint-db." + domain,
                      db_config.get("port"),
                      db_config.get("name"),
                      db_config.get("user"),
                      db_config.get("password"),
                      az_subnets,
                      security_groups = ["InternalSecurityGroup"])

    dynamo_json = open(DYNAMO_SCHEMA, 'r')
    dynamo_cfg = json.load(dynamo_json)
    #config.add_dynamo_table_from_json("EndpointMetaDB",'bossmeta.' + domain, **dynamo_cfg)

    #config.add_redis_replication("Cache", "cache." + domain, az_subnets, ["InternalSecurityGroup"], clusters=1)
    #config.add_redis_replication("CacheState", "cache-state." + domain, az_subnets, ["InternalSecurityGroup"], clusters=1)

    # Allow SSH/HTTP/HTTPS access to endpoint server from anywhere
    config.add_security_group("InternetSecurityGroup",
                              "internet",
                              [
                                ("tcp", "22", "22", INCOMING_SUBNET),
                                ("tcp", "80", "80", "0.0.0.0/0"),
                                ("tcp", "443", "443", "0.0.0.0/0")
                              ])

    return config

def generate(folder, domain):
    """Create the configuration and save it to disk"""
    name = lib.domain_to_stackname("production." + domain)
    config = create_config(None, domain)
    config.generate(name, folder)

def create(session, domain):
    """Configure Vault, create the configuration, and launch it"""
    keypair = lib.keypair_lookup(session)

    def call_vault(command, *args, **kwargs):
        """A wrapper function around lib.call_vault() that populates most of
        the needed arguments."""
        return lib.call_vault(session,
                              lib.keypair_to_file(keypair),
                              "bastion." + domain,
                              "vault." + domain,
                              command, *args, **kwargs)

    db = {
        "name":"boss",
        "user":"testuser",
        "password": lib.generate_password(),
        "port": "3306"
    }

    # Configure Vault and create the user data config that the endpoint will
    # use for connecting to Vault and the DB instance
    endpoint_token = call_vault("vault-provision", "endpoint")
    user_data = configuration.UserData()
    user_data["vault"]["token"] = endpoint_token
    user_data["system"]["fqdn"] = "endpoint." + domain
    user_data["system"]["type"] = "endpoint"
    user_data["aws"]["db"] = "endpoint-db." + domain
    user_data["aws"]["cache"] = "cache." + domain
    user_data["aws"]["cache-state"] = "cache-state." + domain
    user_data["aws"]["meta-db"] = "bossmeta." + domain

    # Should transition from vault-django to vault-write
    call_vault("vault-write", VAULT_DJANGO, secret_key = str(uuid.uuid4()))
    call_vault("vault-write", VAULT_DJANGO_DB, **db)

    try:
        name = lib.domain_to_stackname("production." + domain)
        config = create_config(session, domain, keypair, str(user_data), db)

        success = config.create(session, name)
        if not success:
            raise Exception("Create Failed")
        else:
            # NOTE DP: If an ELB is created the public_uri should be the Public DNS Name
            #          of the ELB. Endpoint Django instances may have to be restarted if running.
            dns = lib.instance_public_lookup(session, "endpoint". domain)
            uri = "http://{}".format(dns)
            call_vault("vault-write", VAULT_DJANGO_AUTH, public_uri = uri)

            # Tell Scalyr to get CloudWatch metrics for these instances.
            instances = [ user_data["system"]["fqdn"] ]
            scalyr.add_instances_to_scalyr(
                session, PRODUCTION_REGION, instances)
    except:
        print("Error detected, revoking secrets")
        try:
            call_vault("vault-delete", VAULT_DJANGO)
            call_vault("vault-delete", VAULT_DJANGO_DB)
        except:
            print("Error revoking Django credentials")
        try:
            call_vault("vault-revoke", endpoint_token)
        except:
            print("Error revoking Endpoint Server Vault access token")
        raise
