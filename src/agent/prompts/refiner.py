from src.agent.state import RepoState

REFINE_PROMPT = """\
You wrote a developer onboarding guide, but a validator found file references that do not exist
in the repository. Fix the guide by correcting or removing each broken reference.

## Repository: {repo_url}

## File Tree (source of truth for valid paths):
{file_tree}

## Validation Errors (broken file references):
{validation_errors}

## Current Draft:
{draft}

## Instructions
- Fix every broken reference listed above
- If the correct path is clear from the file tree, use it
- If there is no matching file, remove the reference entirely or rewrite the sentence without it
- Do not change any content that is not related to the broken references
- Return the complete corrected guide, not just the changed sections
"""


def build_refine_prompt(state: RepoState) -> str:
    errors_str = "\n".join(f"- {e}" for e in state["validation_errors"])

    return REFINE_PROMPT.format(
        repo_url=state["repo_url"],
        file_tree=state["file_tree"][:3000],
        validation_errors=errors_str,
        draft=state["onboarding_draft"],
    )
