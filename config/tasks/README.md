# Plan 24 task bank

`humaneval_plan24_v1.jsonl` holds 8 tasks from OpenAI HumanEval
(https://github.com/openai/human-eval, MIT License, Copyright (c) OpenAI).
Source file `data/HumanEval.jsonl.gz`, sha256
`b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef`.

Frozen before any Plan 24 run: indices `sorted(random.Random(24240).sample(range(164), 8))`
= 28, 34, 55, 56, 81, 85, 98, 137. Alternating owners: alpha_1 gets 28, 55, 81,
98; alpha_2 gets 34, 56, 85, 137. Do not change this file after the first paid
pair; a changed bank needs a new version and a new plan entry.

Agents see only `prompt` (signature and docstring). `test` stays with the
checker and is never written into the world.
