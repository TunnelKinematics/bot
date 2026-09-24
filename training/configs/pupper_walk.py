"""Train a Pupper v3 walking policy (velocity tracking on flat ground).

The CS 123 tasks ship with every reward weight at zero; this script fills them in.
Starting weights come from the Pupper team's original MJX training config
(pupperv3-monorepo: ai/rl/conf/reward/default.yaml), which produced the policies
shipped with the robot. mjlab's term implementations differ in detail, so treat
these as a starting point: judge runs by Metrics/twist/error_vel_xy and
error_vel_yaw on W&B, not by the reward curve.

Usage (from training/, on a Linux machine with an NVIDIA GPU):
  uv run python configs/pupper_walk.py
  uv run python configs/pupper_walk.py --num-envs 2048 --iterations 1500
Set WANDB_API_KEY first, or WANDB_MODE=offline to log locally only.
"""

import argparse

import mjlab.tasks  # noqa: F401  (registers tasks)
from mjlab.scripts.train import TrainConfig, launch_training
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

TASK = "Mjlab-VelocityFS-Flat-Pupper-v3"

REWARD_WEIGHTS = {
  # Objectives
  "track_linear_velocity": 1.5,
  "track_yaw_velocity": 0.8,
  "upright": 0.5,
  "air_time": 0.02,
  "base_height": 0.0,
  "pose": 0.0,
  # Penalties
  "termination": -100.0,
  "orientation_l2": 0.0,
  "lin_vel_z_l2": -0.1,
  "ang_vel_xy_l2": -0.002,
  "foot_slip": -0.2,
  "action_rate_l2": -0.1,
  "joint_torques_l2": -0.025,
  "joint_acc_l2": -1e-6,
  "stand_still_pose": 0.0,
  "stand_still_joint_velocity": -0.2,
  "knee_ground_contact": -10.0,
  "abduction_angle": -0.01,
  "self_collision_l": -0.5,
  "self_collision_r": -0.5,
}

# Domain randomization (the course notebook's defaults).
KP_MULTIPLIER_RANGE = (0.6, 1.1)
KD_MULTIPLIER_RANGE = (0.8, 1.5)
FRICTION_RANGE = (0.6, 1.4)


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument("--task", default=TASK)
  parser.add_argument("--num-envs", type=int, default=4096)
  parser.add_argument("--iterations", type=int, default=3000)
  args = parser.parse_args()

  env_cfg = load_env_cfg(args.task)
  missing = sorted(set(REWARD_WEIGHTS) - set(env_cfg.rewards))
  if missing:
    print(f"[pupper_walk] task has no reward terms {missing}; skipping them")
  for name, weight in REWARD_WEIGHTS.items():
    if name in env_cfg.rewards:
      env_cfg.rewards[name].weight = weight
  env_cfg.events["pd_gains"].params["kp_range"] = KP_MULTIPLIER_RANGE
  env_cfg.events["pd_gains"].params["kd_range"] = KD_MULTIPLIER_RANGE
  env_cfg.events["foot_friction"].params["ranges"] = FRICTION_RANGE
  env_cfg.scene.num_envs = args.num_envs

  agent_cfg = load_rl_cfg(args.task)
  agent_cfg.max_iterations = args.iterations
  agent_cfg.logger = "wandb"

  launch_training(args.task, TrainConfig(env=env_cfg, agent=agent_cfg))


if __name__ == "__main__":
  main()
