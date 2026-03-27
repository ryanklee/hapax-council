---
name: suggest-pr-review
enabled: true
event: bash
pattern: gh pr create|git push.*origin
---

PR created or code pushed. Consider using `/review-pr` (pr-review-toolkit) for automated review before merge.

---
name: suggest-debugging
enabled: true
event: bash
pattern: pytest.*FAILED|Error|error.*traceback|AssertionError
---

Test failure or error detected. Consider using the `superpowers:systematic-debugging` skill — invoke it before proposing fixes.

---
name: suggest-commit
enabled: true
event: prompt
pattern: commit|push|merge|pr
---

Git workflow detected. Available commands: `/commit`, `/commit-push-pr`, `/clean_gone` (commit-commands plugin).

---
name: suggest-sysadmin
enabled: true
event: bash
pattern: systemctl|journalctl|systemd|\.service|\.timer
---

systemd operation detected. The `linux-sysadmin` plugin provides `/sysadmin` for guided troubleshooting.

---
name: suggest-frontend-design
enabled: true
event: file
pattern: \.(tsx|jsx|css|html)$
---

Frontend file being edited. The `frontend-design` plugin skill creates distinctive, production-grade interfaces. Consider using it for new components.

---
name: suggest-pydantic-ai-review
enabled: true
event: file
pattern: agents/.*\.py$
---

Agent file being modified. `beagle-ai` provides `pydantic-ai-*` skills for agent creation, testing, tool systems, and common pitfalls review.

---
name: suggest-hookify
enabled: true
event: prompt
pattern: hook|prevent|block|whenever.*should|every time.*must
---

Behavior automation detected. Use `/hookify` to create a hookify rule that enforces this automatically.

---
name: suggest-playground
enabled: true
event: prompt
pattern: playground|interactive|visualize|preview|demo|explore
---

Interactive visualization request. The `playground` plugin creates self-contained HTML explorers. Use the `playground` skill.

---
name: suggest-claude-md
enabled: true
event: prompt
pattern: claude\.md|CLAUDE\.md|project instructions|update instructions
---

CLAUDE.md management detected. Use `/revise-claude-md` (claude-md-management) for structured auditing and improvement.
