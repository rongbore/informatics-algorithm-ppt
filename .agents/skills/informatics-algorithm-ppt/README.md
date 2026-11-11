# informatics-algorithm-ppt

A Codex-oriented Skill for Chinese interactive C++ algorithm teaching slides.

## Quick start
```bash
python scripts/generate_demo_trace.py
python -m unittest discover -s tests -v
python scripts/validate_trace.py examples/sliding-window/trace.json
```
Copy `examples/sliding-window/trace.json` into `templates/slidev/trace.json` (the demo generator does this automatically in the packaged sample). Then:
```bash
cd templates/slidev
npm install
npm run dev
npm run build
```

This package includes a complete worked demo for monotonic deque/sliding-window maximum, plus reusable agent instructions and architecture for extending to other algorithms. Additional algorithm visualizers must be implemented and validated per family; the sample should not be mistaken for a fully populated curriculum library.
