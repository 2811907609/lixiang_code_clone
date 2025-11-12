# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
# copied from commit bd5f72a

import json
import subprocess
import traceback
from pathlib import Path
from typing import Any

import fire
from datasets import load_dataset  # pyright: ignore
from docker import DockerClient, from_env
from docker.errors import ImageNotFound
from docker.models.containers import Container, ExecResult
from tqdm import tqdm

ubuntu_image = "artifactory.ep.chehejia.com/ep-docker/ubuntu:22.04"
agent_workspace = 'agent-workspace'

_current_file = Path(__file__)
_repo_root = _current_file.parent.parent.parent.parent.parent

_code_repo_in_container = f"/{agent_workspace}/ai-mono-repo"

def docker_exec(container: Container, command: str):
    """
    Execute a command in a docker container.

    Args:
        container: The docker container object.
        command: The command to execute.

    Returns:
        A tuple of (return_code, output).
    """
    exec_result: ExecResult = container.exec_run(cmd=command)  # pyright: ignore[reportUnknownMemberType]
    return_code = exec_result[0]
    output = exec_result[1].decode("utf-8")
    return return_code, output


class SWEBenchEvaluation:
    def __init__(
        self,
        working_dir: str,
        dataset: str = "SWE-bench_Verified",
        docker_env_config: str = "",
        swebench_harness_path: str = "",
        run_id: str = "agent",
        instance_ids: list[str] | None = None,
    ):
        """
        Initialize the SWEBenchEvaluation class. The initialisation includes checking the existence of required Docker images and downloading missing images.

        Args:
            working_dir: The working directory.
            dataset: The dataset to evaluate.
            docker_env_config: The path to the docker environment config file.
            swebench_harness_path: The path to the SWEBench harness.
            run_id: The run id.
            instance_ids: List of specific instance IDs to process. If None, process all instances.
        """
        assert dataset in ["SWE-bench", "SWE-bench_Lite", "SWE-bench_Verified"], (
            f"Invalid dataset name: {dataset}"
        )
        self.dataset = load_dataset(f"princeton-nlp/{dataset}", split="test")
        self.dataset_name = dataset

        self.docker_client: DockerClient = from_env()
        self.image_status: dict[Any, Any] = {}
        self.working_dir = Path(working_dir)
        self.swebench_harness_path = swebench_harness_path
        self.run_id = run_id

        if docker_env_config != "":
            with open(docker_env_config, "r") as f:
                self.docker_env_config: dict[str, dict[str, str]] = json.load(f)
        else:
            self.docker_env_config = {}

        if not self.working_dir.exists():
            self.working_dir.mkdir(parents=True, exist_ok=True)

        self.pull_images(instance_ids)

    def _image_name(self, instance_id: str) -> str:
        """
        Get the image name from the instance id.

        Args:
            instance_id: The instance id.

        Returns:
            The image name.
        """
        key = f"artifactory.ep.chehejia.com/docker-remote/swebench/sweb.eval.x86_64.{instance_id.lower()}:latest"
        key = key.replace("__", "_1776_")
        return key

    def _check_images(self, instance_ids: list[str] | None = None):
        """
        Check the existence of required Docker images.

        Args:
            instance_ids: List of specific instance IDs to check. If None, check all instances.
        """
        if instance_ids:
            # Filter dataset to only include specified instance IDs
            filtered_dataset = [item for item in self.dataset if item["instance_id"] in instance_ids]
            dataset_to_check = filtered_dataset
        else:
            dataset_to_check = self.dataset

        for item in tqdm(dataset_to_check, desc="Checking image status"):  # pyright: ignore[reportUnknownVariableType]
            instance_id: str = item["instance_id"]  # pyright: ignore[reportUnknownVariableType]
            image_name = self._image_name(instance_id)  # pyright: ignore[reportUnknownArgumentType]
            try:
                _ = self.docker_client.images.get(image_name)
                self.image_status[instance_id] = True
            except ImageNotFound:
                self.image_status[instance_id] = False
        try:
            _ = self.docker_client.images.get(ubuntu_image)
        except Exception:
            self.docker_client.images.pull(ubuntu_image)

    def pull_images(self, instance_ids: list[str] | None = None):
        """
        Pull the required Docker images.

        Args:
            instance_ids: List of specific instance IDs to download. If None, download all missing images.
        """
        self._check_images(instance_ids)
        print(f"Total number of images: {len(self.image_status)}")
        missing_instance_ids = [
            instance_id for instance_id in self.image_status if not self.image_status[instance_id]
        ]
        print(f"Number of images to download: {len(missing_instance_ids)}")
        if len(missing_instance_ids) == 0:
            return
        for instance_id in tqdm(missing_instance_ids, desc="Downloading images"):
            image_name = self._image_name(instance_id)
            self.docker_client.images.pull(image_name)

    def prepare_experiment_container(self, instance: dict[str, str]) -> Container:
        """
        Prepare an experiment Docker container for a given instance.

        Args:
            instance: A dictionary containing instance information.

        Returns:
            The Docker container object.
        """
        image_name = self._image_name(instance["instance_id"])

        instance_dir = self.working_dir / instance["instance_id"]
        instance_dir.mkdir(parents=True, exist_ok=True)

        with open(instance_dir / "problem_statement.txt", "w") as f:
            f.write(instance["problem_statement"])

        container: Container = self.docker_client.containers.run(
            image_name,
            command="/bin/bash",
            detach=True,
            tty=True,
            stdin_open=True,
            volumes={
                self.working_dir.absolute().as_posix(): {"bind": f"/{agent_workspace}", "mode": "rw"},
                _repo_root.absolute().as_posix(): {"bind": _code_repo_in_container, "mode": "rw"},
            },
            working_dir=f"/{agent_workspace}",
            environment=self.docker_env_config.get("experiment_env", None),
            stream=True,
        )

        commands = [
            "tar xf uv.tar",
            "mkdir -p /root/.local/bin",
            "cp uv /usr/bin/",
            "mv uv /root/.local/bin/",
            "tar xf uv_shared.tar",
            "mkdir -p /root/.local/share",
            "mv uv /root/.local/share/",
            f"cp {_code_repo_in_container}/deploy/ubuntu2204.sourcelist /etc/apt/sources.list",
            "apt update && apt install -y silversearcher-ag",
            f"cd {_code_repo_in_container}/codebuddy/ai_agents; UV_PROJECT_ENVIRONMENT=./agent-env uv sync --all-groups",
        ]

        for command in commands:
            try:
                new_command = f'/bin/bash -c "{command}"'
                print(f"will execute command {command} in docker")
                return_code, output = docker_exec(container, new_command)
                if return_code is not None and return_code != 0:
                    print("Docker exec error. Error message: {}".format(output))
            except Exception:
                print(f"{command} failed.")
                print(traceback.format_exc())
                break
        return container

    def run_one_instance(self, instance_id: str):
        """
        Run a single instance using the prepared experiment container.

        Args:
            instance_id: The ID of the instance to run.
        """
        instance: dict[str, str] | None = None
        for inst in self.dataset:  # pyright: ignore[reportUnknownVariableType]
            if inst["instance_id"] == instance_id:  # pyright: ignore
                instance = inst  # pyright: ignore
        if instance is None:
            print(f"Instance {instance_id} not found.")
            return

        container = self.prepare_experiment_container(instance)
        instance_dir = instance["instance_id"]
        problem_statement_path = f"/{agent_workspace}/{instance_dir}/problem_statement.txt"
        patch_file_path = f"/{agent_workspace}/{instance_dir}/{instance['instance_id']}.patch"
        traj_path = instance_dir + f"/{instance['instance_id']}.json"

        command = (f"cd {_code_repo_in_container}/codebuddy/ai_agents; "
                   f"source local.env && UV_PROJECT_ENVIRONMENT=./agent-env uv run clis/swebench/cli.py "
                   f"--instance-id {instance_id} "
                   f'--file {problem_statement_path} --working-dir="/testbed/" '
                   f"--config-file trae_config_local.json --max-steps 200  --patch-path {patch_file_path} "
                   f"--trajectory-file {traj_path}")
        new_command = f"/bin/bash -c '{command}'"

        try:
            print(f"will execute command {command} in docker")
            return_code, _ = docker_exec(container, new_command)
            if return_code is not None and return_code != 0:
                print("Docker exec error")
        except Exception:
            print(f"{command} failed.")
            print(traceback.format_exc())

        container.stop()

    def run_all(self):
        """
        Run all instances in the dataset.
        """
        for instance in tqdm(self.dataset, desc="Running all instances"):  # pyright: ignore
            self.run_one_instance(instance["instance_id"])  # pyright: ignore

    def run_eval(self):
        """
        Run evaluation using the SWE-bench harness.
        """
        swebench_harness_path = Path(self.swebench_harness_path)

        cmd = [
            "uv",
            "run",
            "python",
            "-m",
            "swebench.harness.run_evaluation",
            "--dataset_name",
            f"princeton-nlp/{self.dataset_name}",
            "--predictions_path",
            (self.working_dir / "predictions.json").absolute().as_posix(),
            "--run_id",
            self.run_id,
            "--cache_level",
            "instance",
            "--instance_image_tag",
            "latest",
        ]

        process = subprocess.run(cmd, capture_output=True, cwd=swebench_harness_path.as_posix())
        print(process.stdout.decode())
        print(process.stderr.decode())

        result_filename = f"agent.{self.run_id}.json"
        print(f"Evaluation completed and file saved to {result_filename}")

    def get_all_preds(self, instance_ids: list[str] | None = None):
        """
        Get all predictions for a list of instance IDs.

        Args:
            instance_ids: A list of instance IDs. If None, all instances in the dataset will be used.
        """
        preds: list[dict[str, str]] = []
        if not instance_ids:
            instance_ids = [instance["instance_id"] for instance in self.dataset]  # pyright: ignore
        for instance_id in instance_ids:
            patch_path = self.working_dir / instance_id / f"{instance_id}.patch"
            if not patch_path.exists():
                continue
            with open(patch_path, "r") as f:
                patch = f.read()
            preds.append(
                {
                    "instance_id": instance_id,
                    "model_name_or_path": "agent",
                    "model_patch": patch,
                }
            )
        with open(self.working_dir / "predictions.json", "w") as f:
            json.dump(preds, f)


def setup_container(
    instance_id: str,
    dataset: str = "SWE-bench_Verified",
    working_dir: str = f"./{agent_workspace}",
    docker_env_config: str = "",
):
    """
    Setup a test container for a specific instance.

    Args:
        instance_id: The instance ID to setup container for
        dataset: Dataset to use (SWE-bench, SWE-bench_Lite, SWE-bench_Verified)
        working_dir: Working directory path
        docker_env_config: Docker environment config file path

    Returns:
        Container ID that can be used to interact with the container
    """
    evaluation = SWEBenchEvaluation(
        working_dir,
        dataset,
        docker_env_config,
        "",  # swebench_harness_path not needed for setup
        "agent",  # run_id not needed for setup
        [instance_id],
    )

    # Find the instance
    instance = None
    for inst in evaluation.dataset:
        if inst["instance_id"] == instance_id:
            instance = inst
            break

    if instance is None:
        print(f"Instance {instance_id} not found in dataset {dataset}")
        return None

    container = evaluation.prepare_experiment_container(instance)
    print(f"Container {container.id} setup for instance {instance_id}")
    print(f"Problem statement saved to: {working_dir}/{instance_id}/problem_statement.txt")
    print(f"To connect: docker exec -it {container.id} /bin/bash")

    return container.id


def main(
    dataset: str = "SWE-bench_Verified",
    working_dir: str = f"./{agent_workspace}",
    instance_ids: str = "",
    swebench_harness_path: str = "",
    docker_env_config: str = "",
    run_id: str = "agent",
    mode: str = "e2e",
):
    """
    Run SWE-bench evaluation.

    Args:
        dataset: Dataset to evaluate (SWE-bench, SWE-bench_Lite, SWE-bench_Verified)
        working_dir: Working directory path
        instance_ids: Comma-separated instance IDs to run (e.g. "id1,id2,id3"). Leave empty to run all.
        swebench_harness_path: Path to SWE-bench harness (only used for evaluation)
        docker_env_config: Docker environment config file path
        run_id: Run ID for SWE-bench evaluation
        mode: e2e (both expr and eval), expr (only generate patches), eval (only evaluation patches)
    """
    if mode not in ["e2e", "expr", "eval"]:
        raise ValueError(f"Invalid mode: {mode}. Must be one of: e2e, expr, eval")

    # Parse instance_ids from comma-separated string
    parsed_instance_ids = None
    if instance_ids.strip():
        parsed_instance_ids = [id.strip() for id in instance_ids.split(",") if id.strip()]

    evaluation = SWEBenchEvaluation(
        working_dir,
        dataset,
        docker_env_config,
        swebench_harness_path,
        run_id,
        instance_ids=parsed_instance_ids,
    )

    if mode == "e2e" or mode == "expr":
        # Check if required tar files exist instead of building them
        tars = ["uv.tar", "uv_shared.tar"]
        missing_tars = []
        for tar in tars:
            tar_path = evaluation.working_dir / tar
            if not tar_path.exists():
                missing_tars.append(tar)

        if missing_tars:
            print(f"Error: Missing required tar files: {missing_tars}")
            print("Please run deploy/build_artifacts.sh to generate them.")
            exit(1)

        if parsed_instance_ids:
            print(f"Running {len(parsed_instance_ids)} specific instances: {', '.join(parsed_instance_ids)}")
            for instance_id in tqdm(parsed_instance_ids, desc="Running instances"):
                evaluation.run_one_instance(instance_id)
        else:
            print("Running all instances")
            evaluation.run_all()

    if mode == "e2e" or mode == "eval":
        evaluation.get_all_preds(parsed_instance_ids)
        evaluation.run_eval()


def eval(
    dataset: str = "SWE-bench_Verified",
    working_dir: str = f"./{agent_workspace}",
    instance_ids: str = "",
    swebench_harness_path: str = "",
    run_id: str = "agent",
):
    """
    Run SWE-bench evaluation only (without generating patches).

    Args:
        dataset: Dataset to evaluate (SWE-bench, SWE-bench_Lite, SWE-bench_Verified)
        working_dir: Working directory path where predictions are stored
        instance_ids: Comma-separated instance IDs to evaluate (e.g. "id1,id2,id3"). Leave empty to evaluate all.
        swebench_harness_path: Path to SWE-bench harness
        run_id: Run ID for SWE-bench evaluation
    """
    # Parse instance_ids from comma-separated string
    parsed_instance_ids = None
    if instance_ids.strip():
        parsed_instance_ids = [id.strip() for id in instance_ids.split(",") if id.strip()]

    evaluation = SWEBenchEvaluation(
        working_dir,
        dataset,
        "",  # docker_env_config not needed for eval-only
        swebench_harness_path,
        run_id,
        instance_ids=parsed_instance_ids,
    )

    # Generate predictions.json from existing patch files
    evaluation.get_all_preds(parsed_instance_ids)

    # Run evaluation
    evaluation.run_eval()


if __name__ == "__main__":
    fire.Fire({
        'main': main,
        'setup_container': setup_container,
        'eval': eval,
    })
