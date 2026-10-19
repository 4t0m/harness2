"""Heldout priority-selection cases for creative production planning.

Keep authoritative expected choices outside the model-facing task briefs.
"""

TASKS = [
    {
        "task_id": "render_budget_setup_cost",
        "brief": (
            "You have 9 minutes total for this shot, including a 3-minute scene-load "
            "and lighting setup. Choose one production plan from the options."
        ),
        "options": [
            "Load and light (3 min), then render the full-resolution shot (7 min).",
            "Load and light (3 min), then render a half-resolution preview (5 min).",
            "Render the full-resolution shot (7 min) without loading the scene first.",
            "Load and light (3 min), render a half-resolution preview (5 min), then render full resolution (4 min).",
        ],
    },
    {
        "task_id": "preserve_approved_motion_span",
        "brief": (
            "The client approved the character's motion from 2.0 through 4.5 seconds. "
            "Keep every pose and timing in that span unchanged while making the requested "
            "edit outside it. Choose the edit plan."
        ),
        "options": [
            "Retiming the whole clip slightly, including the approved span, then adjusting the ending.",
            "Leave 2.0–4.5 seconds untouched and adjust only the motion after 4.5 seconds.",
            "Smooth the transition by replacing the final half-second of the approved span.",
            "Rebuild the clip from the opening pose and recreate the approved motion by eye.",
        ],
    },
    {
        "task_id": "dependency_before_render",
        "brief": (
            "The render depends on a rig check that confirms the hand controls are connected. "
            "That check has not run yet. Choose what to do next."
        ),
        "options": [
            "Start the final render now and check the hand controls if the result looks wrong.",
            "Run the rig check, fix any disconnected controls, then render after it passes.",
            "Skip the rig check and render a low-quality final to save time.",
            "Render the scene while the rig check runs in parallel, then use whichever finishes first.",
        ],
    },
    {
        "task_id": "single_resource_concurrency",
        "brief": (
            "The only GPU is occupied by an export that must finish before another GPU job "
            "can start. A preview render and an upscale are both queued. Choose the schedule."
        ),
        "options": [
            "Start the preview render and upscale together so both are ready sooner.",
            "Wait for the export to finish, then run the preview render and upscale one at a time.",
            "Start the upscale now and pause the export when GPU use rises.",
            "Run the preview render on the GPU while the export continues on the same GPU.",
        ],
    },
    {
        "task_id": "uncertain_taste_compare",
        "brief": (
            "You are unsure whether the client prefers a warm or cool color grade. They asked "
            "to compare both looks before choosing, and requested no final render yet. Choose "
            "the next step."
        ),
        "options": [
            "Commit to the warm grade and render the final sequence.",
            "Create one low-cost preview in each grade, present them side by side, and wait for a choice.",
            "Blend the warm and cool grades into one final look and render the sequence.",
            "Choose the cool grade based on common client preferences and render the final sequence.",
        ],
    },
    {
        "task_id": "avatar_relative_position",
        "brief": (
            "Place the avatar to the viewer's left of the console, close enough to reach its "
            "controls, and facing the console. Choose the placement."
        ),
        "options": [
            "Place the avatar to the viewer's right of the console, within reach, facing it.",
            "Place the avatar to the viewer's left of the console, within reach, facing it.",
            "Place the avatar to the viewer's left of the console, beyond arm's reach, facing it.",
            "Place the avatar to the viewer's left of the console, within reach, facing away from it.",
        ],
    },
]

EXPECTED_INDICES = {
    "render_budget_setup_cost": 1,
    "preserve_approved_motion_span": 1,
    "dependency_before_render": 1,
    "single_resource_concurrency": 1,
    "uncertain_taste_compare": 1,
    "avatar_relative_position": 1,
}
