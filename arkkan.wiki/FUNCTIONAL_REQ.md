
# `arkkan` Functional Requirements

## Overview

`arkkan` is a PromptDB that serves as a centralized repository for prompt resources, making them available for discovery and retrieval by authorized applications.

`arkkan` enforces a set of access and administration policies to ensure the integrity of the prompt resources and to minimize risk to running software. Consuming applications select and assemble resources into complete prompts; `arkkan` does not assemble prompts.

In Arabic, "arkkan" means **"pillars," "supports," or "corners"** and is the plural of *rukn* (ركن). The PromptDB will be the backbone of software systems.

## What is a Prompt Resource
Prompts are broken down into different independent Resource modules. Each Resource has a type that defines its role and purpose. The LLM or the runtime software constructs the prompt in realtime by pulling the relevant Resource modules together.

A Resource consists of **Resource Metadata**, which identifies and describes it, and **Resource Versions**, which hold its versioned content and lifecycle state.

### Resource Metadata

Resource Metadata includes the slug, name, description, and type. The slug and type cannot change after creation. The name and description may be updated.

### Resource Types

| Resource Type | Description                                                                                                                                                                                                                                         |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Constraints   | Describes a set of constraints that the LLM must comply with.                                                                                                                                                                                       |
| Process       | A process defines a set of instructions that guide the LLM how to complete a specific repetitive task. It has a clear start, logic flow, input/outputs, and an end step. Examples include: *requesting user clarification*, *user driven Q&A*, etc. |
| Rubric        | A rubric resource defines a reusable structured scoring guide with criteria.                                                                                                                                                                        |
| Role          | Defines the expertise, responsibilities, and expected behavior that the LLM must adopt when performing a task. For example, a software architect or a paralegal expert.                                                                               |
| Task          | Defines the objective that the LLM must achieve. It binds all the applicable resources. It is the highest order resource.                                                                                                                           |
| Templates     | These are template documents that the prompt may instruct the LLM to load and complete such as report generation.                                                                                                                                   |
| Extensions    | A generic catch-all extension to the prompt.                                                                                                                                                                                                        |

Resource types are controlled values managed by `arkkan` administrators. The types above are the initial values. Administrators may add new types and delete unused administrator-created types. The seven predefined types cannot be deleted. Type identifiers cannot be renamed; type descriptions may be updated for clarity or correctness.

## Resource Versions
A Resource may have multiple versions. Versions are introduced due to enhancements, upgrades, and general maintenance. To minimize risk, clients can continue to use the same  version of a Resource until they explicitly switch to the new one. 

Resource versions are set by the `arkkan` admin and unique for a particular Resource. Version identifiers are nonempty text values with no required numbering convention or implied ordering, and cannot change after creation.

A version has content, version information, and a lifecycle state. Content cannot change after creation; changes require a new version. Content may be empty in any state. Version information is an optional description of the changes, improvements, or corrections introduced in a resource version, and may be updated.

Each Resource Version has a lifecycle state that determines whether it is available for use. The states and their governing rules are defined in the Resource States section.

New versions may be created as `disabled` (the default), `enabled`, or `enabled_default`, subject to the state policies. They cannot be created as `obsolete`.

## Resource States
Resource states are used to manage a Resource version lifecycle. 

### State Definitions and Transition Paths

| State           | Definition and Read Policies                                                                                         | Allowed State Transition                     |
| --------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| enabled         | - Deployed and active. <br>- Can be retrieved and used by the clients. <br>- The Resource version must be specified. | - enabled_default<br>- disabled              |
| enabled_default | - Deployed and active. <br>- Can be retrieved and used by the clients. <br>- A Resource version is not required.     | - enabled<br>- disabled                      |
| disabled        | - Provisioned but not active.<br>- Cannot be retrieved by the clients, even if the version is specified.             | - enabled<br>- enabled_default<br>- obsolete |
| obsolete        | - Ready for being deleted. <br>- Cannot be retrieved by the clients, even if the version is specified.               | - disabled                                   |

### State Transition Policies

1. A Resource can have up 0 or 1 `enabled_default` state.
2. Changing a Resource state to `enabled_default` automatically alters the current Resource version that is `enabled_default` to `enabled`. There can only be one `enabled_default` as per above policy rule.
3. No resource can lose its `enabled_default` state without making another version `enabled_default`, unless the force option is used. 
4. Only Resource versions that are `obsolete` can be deleted. Deleting the last version does not delete the Resource.
5. A Resource can be deleted if all of its versions are `obsolete`, including when it has no versions. Deleting the Resource and its versions is an all-or-nothing operation.
6. All state changes, including bulk changes, must comply with the state transition policies; invalid operations are rejected without partial changes.


## Security

### Roles

| Role           | Create Table | Modify Table | Drop Table | Add Row | Edit Row | Delete Row | Read | Generate View |
| -------------- | ------------ | ------------ | ---------- | ------- | -------- | ---------- | ---- | ------------- |
| `superuser`    | Yes          | Yes          | Yes        | Yes     | Yes      | Yes        | Yes  | Yes           |
| `arkkan admin` | No           | No           | No         | Yes     | Yes      | Yes        | Yes  | Yes           |
| `arkkan user`  | No           | No           | No         | No      | No       | No         | Yes  | Yes           |

