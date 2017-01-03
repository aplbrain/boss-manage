# AWS Step Function DSL

This document describes a domain specific language (DSL) for AWS Step Function
(SFN) state machines. The using the Python stepfunctions library the DSL can be
compiled down to the [AWS States Language][language definition].

For more information on the Python [stepfunctions library] or its use visit the
libraries page.

    Copyright 2016 The Johns Hopkins University Applied Physics Laboratory

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.


## Table of Contents:

* [Why](#Why)
* [Style](#Style)
* [Structure](#Structure)
* [Concepts](#Concepts)
  - [Error Names](#Error-Names)
  - [Timestamps](#Timestamps)
  - [JsonPath](#JsonPath)
* [Top-Level Fields](#Top-Level-Fields)
* [States](#States)
  - [Basic States](#Basic-States)
    - [Success State](#Success-State)
    - [Fail State](#Fail-State)
    - [Pass State](#Pass-State)
    - [Task State](#Task-State)
    - [Wait State](#Wait-State)
  - [Flow Control States](#Flow-Control-States)
    - [Comparison Operators](#Comparison-Operators)
    - [If](#If)
    - [While Loop](#While-Loop)
    - [Parallel](#Parallel)

## Why
When Amazon released AWS Step Functions they provided a [language definition]
for writing state machine in. While functional, it is cumbersome to write and
maintain state machines in their Json format. This DSL is designed to make it
easier to read, write, and maintain step function state machines.

The biggest benefit of using the DSL for writing a state machine is that when
compiled to the AWS Json format by a library like [stepfunctions library] the
states can be automatically linked together, instead of manually having to
specify the next state for each state.

The single flow control state has be translated into two of the basic flow
control operations used in programming (if/elif/else and while loop).

## Style
The DSL's style is influenced by Python code style.

* It is an indent based language where the level of indent is used to specify a
  block of code.
* Strings can be defined using `'`, `"`, `'''`, `"""`
* Doc String style comments for states

## Structure
The SFN DSL format is an optional top level comment followed by a list of states.

### Example
    """Simple Example of the SFN DSL"""
    Lambda('HelloWorld')

Execution of the state machine is started at the first state in the file and
execution proceedes until the state at the end of the file is reached or until
a state terminates execution.

In this example there is one state. The full ARN for the Lambda will be determined
when the DSL is compiled into the AWS Json format. The full ARN can be passed if
the desired Lambda doesn't reside in the same account or region as the connection
used to compile and create the state machine.

## Concepts
### Error Names
There is a predefined set of basic errors that can happen.
[State machine errors reference][language definition errors].

### Timestamps
The SFN DSL supports comparison against timestamp values. The way a timestamp is
determined, compared to a regular string, is that it can be parsed as a timestamp
according to RFC3339. This format often looks like `yyyy-mm-ddThh:mm:ssZ`. If a
timestamp is not in the correct format the comparison will be performed as a
string comparison.

### JsonPath
State machines use a version of JsonPath for referencing data that is is being
processed. [State machine path reference][language definition path].

## Top-Level Fields
A SFN DSL file consists of three optional fields followed by a list of States.

    """State machine comment"""
    version: "1.0"
    timeout: int

The top level comment is the comment for the state machine that is created.

* `version`: Is a string of the version number of the State Machine language to
             compile down to. Currently only `"1.0"` is supported.
* `timeout`: The overall timeout in seconds for the whole state machine execution.
             If the state machine has not finished execution within this time
             the execution fails with a `States.Timeout` error.

## States
The different types of state machine states are divided into two categories.
Basic states are those that perform a single action and, potentially, link to
another state. Flow control states are those that apply some flow control logic.

### Basic States
#### Success State
A terminal state, `Success()` will cause the state machine to terminate execution
successfully and return a result value.

    Success()
        """State Name
        State Comment"""
        input: JsonPath
        output: JsonPath

States can have a Python style doc string. If given, the first line of the doc
string is the state's name and the rest if the states comment. If no name is given
(or an empty name) the state's name is built from the line number.

Modifiers:
* `input`: JsonPath selecting a value from the input object to be passed to the
           current state (Default: `"$"`)
* `output`: JsonPath selecting a value from the output object to be passed to the
            next state (Default: `"$"`)

#### Fail State
A terminal state, `Fail()` will cause the state machine to terminate execution
unsuccessfully with the given error and cause values.

    Fail(error, cause)
        """State Name
        State Comment"""

Arguments:
* `error`: String containing the error value
* `cause`: String containing the error's cause, a more readable value

#### Pass State
A state that does nothing `Pass()` can be used to modify the data being passed
around or inject new data into the results.

    Pass()
        """State Name
        State Comment"""
        input: JsonPath
        result: JsonPath
        output: JsonPath
        data:
            Json

Modifiers:
* `result`: JsonPath of where to place the results of the state, relative to the
            raw input (before the `input` modifier was applied) (Default: `"$"`)
* `data`: A block of Json data that will be used as the result of the state

#### Task State
There are two types of task states, `Lambda()` and `Activity()`. The difference
is where the code that will be executed is living. For `Lambda()` the code is a
AWS Lambda function. For `Activity()` the code can be running anywhere, and is
responsible for polling AWS to see if there is new work for it to perform. Both
states are like function calls, where input it taken, processing is done, and a
result is returned.

Activity ARNs are created in the Step Functions section of AWS (console or API).
Once defined multiple workers can start polling for work and state machines can send
data to the worker(s) for processing.

    Lambda(name)
    Activity(name)
        """State Name
        State Comment"""
        timeout: int
        heartbeat: int
        input: JsonPath
        result: JsonPath
        output: JsonPath
        retry error(s) retry interval (seconds), max attempts, backoff rate
        catch error(s):
            State(s)

Arguments:
* `name`: Full or partial ARN of the Lambda or Activity. A partial ARN leaves some
          of the begining of the ARN off, to be automatically filled in during
          compilation time. The farthest that this can be taken is just passing
          the name of the Lambda or Activity.

Modifiers:
* `timeout`: Number of seconds before the task times out (Default: 60 seconds)
* `heatbeat`: Number of seconds before the task times out if no heartbeat has been
              received from the task. Needs to be less than the `timeout` value.
* `retry`: If the given error(s) were encountered, rerun the state
  - `error(s)`: A single string, array of strings, or empty array of errors to match
              against. An empty array matches against all errors.
  - `retry interval`: Number of seconds to wait before the first retry
  - `max attempts`: Number of retries to attempt before passing errors to `catch`
                  modifiers. Zero (0) is a valid value, meaning don't retry.
  - `backoff rate`: The multipler that increases the `retry interval` on each attempt
* `catch`: If the given error(s) were encountered and not handled by a `retry`
           then execute the given states. If the states in the catch block don't
           terminate, then execution will continue on the next valid state.
  - `error(s)`: A single string, array of strings, or empty array of errors to match
              against. An empty array matches against all errors.

Note: Ordering of everything besides `retry` and `catch` is currently fixed. There
      can be multiple `retry` and `catch` statements and there is no ordering of
      those modifiers.

#### Wait State
There are four different versions of the `Wait()` state, but each pauses execution
for a given amount of time.

    Wait(seconds=int)
    Wait(timestamp='yyyy-mm-ddThh:mm:ssZ')
    Wait(seconds_path=JsonPath)
    Wait(timestamp_path=JsonPath)
        """State Name
        State Comment"""
        input: JsonPath
        output: JsonPath

Arguments:
* `seconds`: Number of seconds to wait
* `timestamp`: Wait until the specified time
* `seconds_path`: Read the number of seconds to wait from the given JsonPath
* `timestamp_path`: Read the timestamp to wait until from the givne JsonPath

### Flow Control States
#### Comparison Operators

Value Type | Supported Operators
-----------|--------------------
Boolean    | ==, !=
Integer    | ==, !=, <, >, <=, >=
Float      | ==, !=, <, >, <=, >=
String     | ==, !=, <, >, <=, >=
Timestamp  | ==, !=, <, >, <=, >=

Comparison operators can be composed using (order of list is order of precedence):
* ()
* not
* and
* or

#### If
The basic `if` statement. Multiple (or no) `elif` statements can be included. The
`else` statement is also optional.

    if JsonPath operator value:
        """State Name
        State Comment"""
        State(s)
    elif JsonPath operator value:
        State(s)
    else:
        State(s)
    transform:
        input: JsonPath
        result: JsonPath
        output: JsonPath

The `transform` block contains the same `input`, `result`, and `output` modifiers
are the simple states use.

#### While Loop
The basic `while` loop the continues to execute the given states until the condition
is no longer true.

    while JsonPath operator value:
        """State Name
        State Comment"""
        State(s)
    transform:
        input: JsonPath
        result: JsonPath
        output: JsonPath

#### Parallel
The `parallel` control structure allows running multiple branches of execution
in parallel. The parallel state waits until all branches have finished before
moving to the next state. If there is any unhandled error in any branch, the
whole state is considered to have failed.

The state's input is passed to the first state in each branch and the results of
the parallel state is an array of outputs from each branch.

    parallel:
        """State Name
        State Comment"""
        State(s)
    parallel:
        State(s)
    transform:
        input: JsonPath
        result: JsonPath
        output: JsonPath
    error:
        retry error(s) retry interval (seconds), max attempts, backoff rate
        catch error(s):
            State(s)

The `error` block contains the same `retry` and `catch` modifiers as the task state.

[stepfunctions library]: https://github.com/aplmicrons/stepfunctions
[language definition]: https://states-language.net/spec.html
[language definition errors]: https://states-language.net/spec.html#appendix-a
[language definition path]: https://states-language.net/spec.html#path
