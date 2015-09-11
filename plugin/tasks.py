########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


# ctx is imported and used in operations
#from cloudify import ctx
from cloudify.workflows import ctx

# put the operation decorator on any function that is a task
#from cloudify.decorators import operation
from cloudify.decorators import workflow
from cloudify.workflows.tasks_graph import forkjoin

@workflow
def run_test(operation, type_name, operation_kwargs, is_node_operation, **kwargs):
    graph = ctx.graph_mode()

    send_event_starting_tasks = {}
    send_event_done_tasks = {}

    for node in ctx.nodes:
        if type_name in node.type_hierarchy:
            for instance in node.instances:
                send_event_starting_tasks[instance.id] = instance.send_event('Starting to run operation')
                send_event_done_tasks[instance.id] = instance.send_event('Done running operation')

    for node in ctx.nodes:
        if type_name in node.type_hierarchy:
            for instance in node.instances:

                sequence = graph.sequence()

                if is_node_operation:
                    operation_task = instance.execute_operation(operation, kwargs=operation_kwargs)
                else:
                    forkjoin_tasks = []
                    for relationship in instance.relationships:
                        forkjoin_tasks.append(relationship.execute_source_operation(operation))
                        forkjoin_tasks.append(relationship.execute_target_operation(operation))
                    operation_task = forkjoin(*forkjoin_tasks)

                sequence.add(
                    send_event_starting_tasks[instance.id],
                    operation_task,
                    send_event_done_tasks[instance.id])

    for node in ctx.nodes:
        for instance in node.instances:
            for rel in instance.relationships:

                instance_starting_task = send_event_starting_tasks.get(instance.id)
                target_done_task = send_event_done_tasks.get(rel.target_id)

                if instance_starting_task and target_done_task:
                    graph.add_dependency(instance_starting_task, target_done_task)

    return graph.execute()
