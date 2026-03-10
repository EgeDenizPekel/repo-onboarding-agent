import asyncio

import git


async def get_git_log(repo_path: str, n: int = 10) -> list[dict]:
    """Return the last N commits: hash, author, message, date."""

    def _get_log() -> list[dict]:
        repo = git.Repo(repo_path)
        commits = []
        for commit in list(repo.iter_commits(max_count=n)):
            commits.append({
                "hash": commit.hexsha[:8],
                "author": str(commit.author),
                "message": commit.message.strip(),
                "date": commit.committed_datetime.isoformat(),
            })
        return commits

    return await asyncio.to_thread(_get_log)
