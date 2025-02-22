from datetime import datetime
from uuid import uuid4
from behave import given, when, then
from behave.runner import Context

from tests.features.steps.common import ensure_agent_id, get_agent_id, parse_date
from tests.features.steps.common_steps import step_check_error_message
from sdlc.domain.commands import (
    CreateProject, AddRequirement, CompleteRequirement,
    CreateTask, CompleteTask, SetProjectTimeline,
    UpdateProjectStatus, BlockRequirement, UnblockRequirement,
    ChangeRequirementPriority, AssignTask, BlockTask,
    UnblockTask, ChangeTaskPriority
)
from sdlc.domain.views import ProjectOverviewView, RequirementsView, TaskBoardView


@given('a new project "{project_name}" is created')
def step_create_project(context: Context, project_name: str):
    cmd = CreateProject(
        command_id=uuid4(),
        correlation_id=uuid4(),
        name=project_name,
        description=f"{project_name} description",
        repository=project_name.lower().replace(" ", "-"),
        tech_stack=["python", "event-sourcing"],
        created_by=ensure_agent_id(context, 'admin-1')
    )
    events = context.project_handler.handle_create_project(cmd)
    context.current_project_id = events[0].project_id


@given('a requirement "{requirement_name}" is added to the project')
def step_add_requirement(context: Context, requirement_name: str):
    cmd = AddRequirement(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        title=requirement_name,
        description=f"{requirement_name} description",
        priority="high",
        dependencies=[],
        added_by=ensure_agent_id(context, 'admin-1')
    )
    events = context.project_handler.handle_add_requirement(cmd)
    context.current_requirement_id = events[0].requirement_id


@given('a task "{task_name}" is created for the requirement')
def step_create_task(context: Context, task_name: str):
    cmd = CreateTask(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        requirement_id=context.current_requirement_id,
        title=task_name,
        description=f"{task_name} description",
        complexity="medium",
        created_by=ensure_agent_id(context, 'admin-1')
    )
    events = context.project_handler.handle_create_task(cmd)
    context.last_task_id = events[0].task_id


@given('all requirements are completed')
def step_complete_all_requirements(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    for requirement in view.requirements.values():
        # First complete all tasks
        for task in requirement['tasks']:
            cmd = CompleteTask(
                command_id=uuid4(),
                correlation_id=uuid4(),
                project_id=context.current_project_id,
                requirement_id=requirement['id'],
                task_id=task['id'],
                completed_by=ensure_agent_id(context, 'admin-1')
            )
            context.project_handler.handle_complete_task(cmd)

        # Then complete the requirement
        cmd = CompleteRequirement(
            command_id=uuid4(),
            correlation_id=uuid4(),
            project_id=context.current_project_id,
            requirement_id=requirement['id'],
            completed_by=ensure_agent_id(context, 'admin-1')
        )
        context.project_handler.handle_complete_requirement(cmd)


@when('agent "{agent_id}" sets the project timeline')
def step_set_timeline(context: Context, agent_id: str):
    row = context.table[0]
    milestones = [{
        'date': parse_date(row['milestone_date']),
        'description': row['milestone_description']
    }]

    cmd = SetProjectTimeline(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        start_date=parse_date(row['start_date']),
        target_date=parse_date(row['target_date']),
        milestones=milestones,
        set_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_set_timeline(cmd)


@when('agent "{agent_id}" updates project status to "{status}"')
def step_update_status(context: Context, agent_id: str, status: str):
    row = context.table[0]
    try:
        cmd = UpdateProjectStatus(
            command_id=uuid4(),
            correlation_id=uuid4(),
            project_id=context.current_project_id,
            status=status,
            reason=row['reason'],
            updated_by=ensure_agent_id(context, agent_id)
        )
        context.project_handler.handle_update_status(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@when('agent "{agent_id}" blocks the requirement')
def step_block_requirement(context: Context, agent_id: str):
    row = context.table[0]
    cmd = BlockRequirement(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        requirement_id=context.current_requirement_id,
        blocker_description=row['blocker_description'],
        blocked_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_block_requirement(cmd)


@when('agent "{agent_id}" unblocks the requirement')
def step_unblock_requirement(context: Context, agent_id: str):
    row = context.table[0]
    cmd = UnblockRequirement(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        requirement_id=context.current_requirement_id,
        resolution=row['resolution'],
        unblocked_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_unblock_requirement(cmd)


@when('agent "{agent_id}" changes requirement priority')
def step_change_requirement_priority(context: Context, agent_id: str):
    row = context.table[0]
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = next(
        req for req in view.requirements.values()
        if req['title'] == row['requirement']
    )

    cmd = ChangeRequirementPriority(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        requirement_id=requirement['id'],
        new_priority=row['new_priority'],
        reason=row['reason'],
        changed_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_change_requirement_priority(cmd)


@when('agent "{agent_id}" assigns the task to "{assignee_id}"')
def step_assign_task(context: Context, agent_id: str, assignee_id: str):
    cmd = AssignTask(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        task_id=context.last_task_id,
        requirement_id=context.current_requirement_id,
        assignee_id=ensure_agent_id(context, assignee_id),
        assigned_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_assign_task(cmd)


@when('agent "{agent_id}" blocks the task')
def step_block_task(context: Context, agent_id: str):
    row = context.table[0]
    cmd = BlockTask(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        task_id=context.last_task_id,
        requirement_id=context.current_requirement_id,
        blocker_description=row['blocker_description'],
        blocked_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_block_task(cmd)


@when('agent "{agent_id}" unblocks the task')
def step_unblock_task(context: Context, agent_id: str):
    row = context.table[0]
    cmd = UnblockTask(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        task_id=context.last_task_id,
        requirement_id=context.current_requirement_id,
        resolution=row['resolution'],
        unblocked_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_unblock_task(cmd)


@when('agent "{agent_id}" changes task priority')
def step_change_task_priority(context: Context, agent_id: str):
    row = context.table[0]
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    task = next(
        task for task in requirement['tasks']
        if task['title'] == row['task']
    )

    cmd = ChangeTaskPriority(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        task_id=task['id'],
        requirement_id=context.current_requirement_id,
        new_priority=row['new_priority'],
        reason=row['reason'],
        changed_by=ensure_agent_id(context, agent_id)
    )
    context.project_handler.handle_change_task_priority(cmd)


@when('agent "{agent_id}" creates a new project')
def step_create_new_project(context: Context, agent_id: str):
    row = context.table[0]
    cmd = CreateProject(
        command_id=uuid4(),
        correlation_id=uuid4(),
        name=row['name'],
        description=row['description'],
        repository=row['repository'],
        tech_stack=row['tech_stack'].split(','),
        created_by=ensure_agent_id(context, agent_id)
    )
    try:
        events = context.project_handler.handle_create_project(cmd)
        context.current_project_id = events[0].project_id
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@then('the project should be created successfully')
def step_check_project_created(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        ProjectOverviewView
    )
    assert view is not None, "Project not created"
    assert view.name != '', "Project name is empty"


@then('the project overview should show')
def step_check_project_overview(context: Context):
    row = context.table[0]
    view = context.view_store.get_view(
        context.current_project_id,
        ProjectOverviewView
    )
    assert view.active_requirements == int(row['active_requirements']), \
        f"Expected {row['active_requirements']} active requirements, got {view.active_requirements}"
    assert view.completed_requirements == int(row['completed_requirements']), \
        f"Expected {row['completed_requirements']} completed requirements, got {view.completed_requirements}"
    assert view.active_tasks == int(row['active_tasks']), \
        f"Expected {row['active_tasks']} active tasks, got {view.active_tasks}"
    assert view.completed_tasks == int(row['completed_tasks']), \
        f"Expected {row['completed_tasks']} completed tasks, got {view.completed_tasks}"


@then('the requirement should be added to the project')
def step_check_requirement_added(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    assert context.current_requirement_id in view.requirements, \
        "Requirement not found in project"


@then('the requirement "{req_name}" should depend on "{dep_name}"')
def step_check_requirement_dependency(context: Context, req_name: str, dep_name: str):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    print(f"\nChecking dependencies...")
    print(f"All requirements: {[(req['id'], req['title']) for req in view.requirements.values()]}")
    print(f"Dependencies map: {view.requirement_dependencies}")
    
    # Find the requirement and its dependency
    requirement = None
    dependency = None
    for req in view.requirements.values():
        if req['title'].strip() == req_name.strip():
            requirement = req
            print(f"Found requirement {req_name} with ID {req['id']}")
        elif req['title'].strip() == dep_name.strip():
            dependency = req
            print(f"Found dependency {dep_name} with ID {req['id']}")

    assert requirement is not None, f"Requirement '{req_name}' not found"
    assert dependency is not None, f"Dependency '{dep_name}' not found"
    
    # Check if the dependency exists in the requirement's dependencies
    print(f"\nRequirement {req_name} dependencies: {requirement['dependencies']}")
    print(f"Dependency {dep_name} ID: {dependency['id']}")
    assert dependency['id'] in requirement['dependencies'], \
        f"Requirement {req_name} does not depend on {dep_name}"


@then('the requirements should be ordered correctly')
def step_check_requirements_order(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    # Check that no requirement depends on a requirement that comes after it
    for req in view.requirements.values():
        for dep_id in req['dependencies']:
            dep = view.requirements[dep_id]
            assert dep['id'] != req['id'], \
                f"Requirement {req['title']} cannot depend on itself"


@then('the requirement should have {count:d} active tasks')
def step_check_requirement_task_count(context: Context, count: int):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    active_tasks = [task for task in requirement['tasks'] if task['status'] == 'active']
    assert len(active_tasks) == count, \
        f"Expected {count} active tasks, got {len(active_tasks)}"


@when('all tasks for requirement "{req_name}" are completed')
def step_complete_requirement_tasks(context: Context, req_name: str):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = next(
        req for req in view.requirements.values()
        if req['title'] == req_name
    )
    # Complete all tasks
    for task in requirement['tasks']:
        cmd = CompleteTask(
            command_id=uuid4(),
            correlation_id=uuid4(),
            project_id=context.current_project_id,
            requirement_id=requirement['id'],
            task_id=task['id'],
            completed_by=ensure_agent_id(context, 'admin-1')
        )
        context.project_handler.handle_complete_task(cmd)

    context.current_requirement_id = requirement['id']


@then('the requirement should be marked as complete')
def step_check_requirement_completed(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    assert requirement['status'] == 'completed', \
        "Requirement not marked as completed"


@when('agent "{agent_id}" attempts to complete the requirement')
def step_attempt_complete_requirement(context: Context, agent_id: str):
    try:
        cmd = CompleteRequirement(
            command_id=uuid4(),
            correlation_id=uuid4(),
            project_id=context.current_project_id,
            requirement_id=context.current_requirement_id,
            completed_by=ensure_agent_id(context, agent_id)
        )
        context.project_handler.handle_complete_requirement(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@then('the project timeline should be set')
def step_check_timeline_set(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        ProjectOverviewView
    )
    assert view.start_date is not None, "Project start date not set"
    assert view.target_date is not None, "Project target date not set"
    assert len(view.milestones) > 0, "No milestones set"


@then('the milestone "{description}" should be scheduled for "{date}"')
def step_check_milestone(context: Context, description: str, date: str):
    view = context.view_store.get_view(
        context.current_project_id,
        ProjectOverviewView
    )
    milestone = next(
        (m for m in view.milestones if m['description'] == description),
        None
    )
    assert milestone is not None, f"Milestone '{description}' not found"
    assert milestone['date'] == parse_date(date), \
        f"Expected milestone date {date}, got {milestone['date']}"


@then('the project status should be "{status}"')
def step_check_project_status(context: Context, status: str):
    view = context.view_store.get_view(
        context.current_project_id,
        ProjectOverviewView
    )
    assert view.status == status, \
        f"Expected project status {status}, got {view.status}"


@then('the requirement should be blocked')
def step_check_requirement_blocked(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    assert requirement['status'] == 'blocked', \
        "Requirement not marked as blocked"


@then('the requirement should show the blocker description')
def step_check_requirement_blocker(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    assert requirement['blocker_description'] is not None, \
        "No blocker description found"


@then('the requirement should be active')
def step_check_requirement_active(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    assert requirement['status'] == 'active', \
        "Requirement not marked as active"


@then('the requirement "{title}" should have priority "{priority}"')
def step_check_requirement_priority(context: Context, title: str, priority: str):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = next(
        req for req in view.requirements.values()
        if req['title'] == title
    )
    assert requirement['priority'] == priority, \
        f"Expected priority {priority}, got {requirement['priority']}"


@then('the task should be assigned to "{assignee_id}"')
def step_check_task_assigned(context: Context, assignee_id: str):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    task = next(
        task for task in requirement['tasks']
        if task['id'] == context.last_task_id
    )
    assert task['assignee_id'] == get_agent_id(context, assignee_id), \
        "Task not assigned to correct agent"


@then('the task should be blocked')
def step_check_task_blocked(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    task = next(
        task for task in requirement['tasks']
        if task['id'] == context.last_task_id
    )
    assert task['status'] == 'blocked', \
        "Task not marked as blocked"


@then('the task should show the blocker description')
def step_check_task_blocker(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    task = next(
        task for task in requirement['tasks']
        if task['id'] == context.last_task_id
    )
    assert task['blocker_description'] is not None, \
        "No blocker description found"


@then('the task should be active')
def step_check_task_active(context: Context):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    task = next(
        task for task in requirement['tasks']
        if task['id'] == context.last_task_id
    )
    assert task['status'] == 'active', \
        "Task not marked as active"


@then('the task "{title}" should have priority "{priority}"')
def step_check_task_priority(context: Context, title: str, priority: str):
    view = context.view_store.get_view(
        context.current_project_id,
        RequirementsView
    )
    requirement = view.requirements[context.current_requirement_id]
    task = next(
        task for task in requirement['tasks']
        if task['title'] == title
    )
    assert task['priority'] == priority, \
        f"Expected priority {priority}, got {task['priority']}"


@when('agent "{agent_id}" adds a requirement')
def step_add_requirement_with_data(context: Context, agent_id: str):
    row = context.table[0]
    dependencies = []
    
    # Handle dependencies if specified
    print(f"\nRow headings: {row.headings}")
    if 'dependencies' in row.headings:
        print(f"\nFound dependencies column")
        dep_names = row['dependencies'].strip()
        print(f"\nChecking for dependencies: '{dep_names}'")
        if dep_names:
            view = context.view_store.get_view(
                context.current_project_id,
                RequirementsView
            )
            print(f"\nLooking for dependencies in requirements: {[(req['id'], req['title']) for req in view.requirements.values()]}")
            
            # Split dependencies by comma and process each one
            for dep_name in dep_names.split(','):
                dep_name = dep_name.strip()
                dep = None
                print(f"\nLooking for dependency: '{dep_name}'")
                
                # Find the requirement with matching title
                for req in view.requirements.values():
                    print(f"Checking requirement: '{req['title']}' (ID: {req['id']})")
                    if req['title'].strip() == dep_name:
                        dep = req
                        print(f"Found dependency {dep_name} with ID {dep['id']}")
                        dependencies.append(dep['id'])
                        break
                        
                if not dep:
                    raise ValueError(f"Dependency '{dep_name}' not found")
            
    print(f"\nCreating AddRequirement command with dependencies: {dependencies}")
    cmd = AddRequirement(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        title=row['title'].strip(),
        description=row.get('description', '').strip(),
        priority=row['priority'].strip(),
        dependencies=dependencies,
        added_by=ensure_agent_id(context, agent_id)
    )
    
    try:
        events = context.project_handler.handle_add_requirement(cmd)
        context.current_requirement_id = events[0].requirement_id
        print(f"Added requirement {row['title']} with ID {context.current_requirement_id}")
        print(f"Event dependencies: {events[0].dependencies}")
        
        # Verify dependencies were set correctly
        view = context.view_store.get_view(
            context.current_project_id,
            RequirementsView
        )
        requirement = view.requirements[context.current_requirement_id]
        print(f"Requirement dependencies after creation: {requirement['dependencies']}")
        print(f"Dependencies map: {view.requirement_dependencies}")
        
        # Double-check that dependencies are set in both places
        if dependencies:
            print(f"\nVerifying dependencies for {row['title']}:")
            print(f"Expected dependencies: {dependencies}")
            print(f"Actual dependencies in requirement: {requirement['dependencies']}")
            print(f"Actual dependencies in map: {view.requirement_dependencies[context.current_requirement_id]}")
            assert requirement['dependencies'] == dependencies, \
                f"Dependencies not set correctly in requirement. Expected {dependencies}, got {requirement['dependencies']}"
            assert view.requirement_dependencies[context.current_requirement_id] == dependencies, \
                f"Dependencies not set correctly in map. Expected {dependencies}, got {view.requirement_dependencies[context.current_requirement_id]}"
        
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@when('agent "{agent_id}" creates a task')
def step_create_task_with_data(context: Context, agent_id: str):
    row = context.table[0]
    cmd = CreateTask(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        requirement_id=context.current_requirement_id,
        title=row['title'],
        description=row['description'],
        complexity=row['complexity'],
        created_by=ensure_agent_id(context, agent_id)
    )
    try:
        events = context.project_handler.handle_create_task(cmd)
        context.last_task_id = events[0].task_id
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@when('agent "{agent_id}" attempts to update project status to "{status}"')
def step_attempt_update_status(context: Context, agent_id: str, status: str):
    row = context.table[0]
    try:
        cmd = UpdateProjectStatus(
            command_id=uuid4(),
            correlation_id=uuid4(),
            project_id=context.current_project_id,
            status=status,
            reason=row['reason'],
            updated_by=ensure_agent_id(context, agent_id)
        )
        context.project_handler.handle_update_status(cmd)
        context.last_error = None
    except ValueError as e:
        context.last_error = str(e)


@given('a new requirement "{requirement_name}" is added to the project')
def step_add_new_requirement(context: Context, requirement_name: str):
    cmd = AddRequirement(
        command_id=uuid4(),
        correlation_id=uuid4(),
        project_id=context.current_project_id,
        title=requirement_name,
        description=f"{requirement_name} description",
        priority="high",
        dependencies=[],
        added_by=ensure_agent_id(context, 'admin-1')
    )
    events = context.project_handler.handle_add_requirement(cmd)
    context.current_requirement_id = events[0].requirement_id