# Pupper v3 locomotion training

A trimmed copy of [pupper-mjlab](https://github.com/cs123-stanford/pupper-mjlab)
(Stanford CS 123), itself a fork of [mjlab](https://github.com/mujocolab/mjlab)
(Apache-2.0, see `LICENSE`). Only the Pupper robot and tasks are kept. Other
robots, tasks, docs and tooling were removed, and the dependencies live in the
root `pyproject.toml` under the `training` extra.

## Train

Needs Linux with an NVIDIA GPU (macOS can only evaluate). From the repo root:

```bash
uv sync --extra training
export WANDB_API_KEY=...          # or WANDB_MODE=offline
uv run python training/configs/pupper_walk.py
```

The CS 123 tasks ship with every reward weight at zero; `configs/pupper_walk.py`
sets them, starting from the Pupper team's original MJX config. Judge runs by
`Metrics/twist/error_vel_xy` and `error_vel_yaw` on W&B, not the reward curve.

## Other commands

```bash
uv run --extra training list-envs
uv run --extra training play Mjlab-VelocityFS-Flat-Pupper-v3 --wandb-run-path <entity>/mjlab/<run-id>
uv run --extra training export-pupper-policy Mjlab-VelocityFS-Flat-Pupper-v3 --wandb-run-path mjlab/<run-id>
uv run --extra training pytest training/tests
```

Runs upload `policy.json` to W&B when they finish. It is deployed to the robot
with [pupper_gait_deploy](https://github.com/cs123-stanford/pupper_gait_deploy).

## Layout

- `configs/pupper_walk.py`: our training entry point (reward weights, randomization)
- `src/mjlab/asset_zoo/robots/pupper_v3/`: Pupper model and constants
- `src/mjlab/tasks/pupper/`, `pupper_gait/`: Pupper tasks, exporter, runner
- `src/mjlab/tasks/velocity/`: shared velocity-task base the Pupper tasks build on
- `src/mjlab/` (rest): the mjlab framework
