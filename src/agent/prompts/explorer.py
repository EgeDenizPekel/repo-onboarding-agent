FILE_SUMMARY_PROMPT = """\
Summarize this source file for a developer onboarding guide.

File: {file_path}
Language: {language}

Content:
```
{content}
```

Write 2-4 sentences covering:
- What this file does
- Key classes, functions, or exports (use actual names from the code)
- How it fits into the larger system (if apparent)

Be specific. Keep it under 150 words.
"""


def build_file_summary_prompt(file_path: str, language: str, content: str) -> str:
    return FILE_SUMMARY_PROMPT.format(
        file_path=file_path,
        language=language,
        content=content,
    )
