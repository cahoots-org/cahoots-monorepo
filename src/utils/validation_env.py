"""Validation environment for testing implementations."""
import os
import json
import asyncio
import docker
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from ..utils.logger import Logger

logger = Logger("ValidationEnvironment")

class ValidationEnvironment:
    """Environment for validating implementations in isolation."""

    def __init__(self):
        """Initialize validation environment."""
        self.temp_dir = None
        self.container = None
        self.docker_client = docker.from_env()

    async def setup(self, tech_stack: str, dependencies: List[str]) -> None:
        """Set up validation environment.
        
        Args:
            tech_stack: Technology stack being used
            dependencies: List of dependencies to install
        """
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {self.temp_dir}")

        # Install dependencies
        await self._install_dependencies(tech_stack, dependencies)

    async def cleanup(self) -> None:
        """Clean up validation environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary directory")

        if self.container:
            self.container.stop()
            self.container.remove()
            logger.info("Cleaned up Docker container")

    async def _install_dependencies(self, tech_stack: str, dependencies: List[str]) -> None:
        """Install required dependencies.
        
        Args:
            tech_stack: Technology stack being used
            dependencies: List of dependencies to install
        """
        if tech_stack == "python":
            process = await asyncio.create_subprocess_exec(
                "pip",
                "install",
                *dependencies,
                cwd=self.temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

    async def _run_static_analysis(self, tech_stack: str) -> Dict[str, Any]:
        """Run static analysis checks.
        
        Args:
            tech_stack: Technology stack being used
            
        Returns:
            Dict containing static analysis results
        """
        results = {
            "ruff_results": [],
            "radon_results": [],
            "issues_found": 0
        }

        if tech_stack == "python":
            # Run Ruff for linting
            process = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                "--format=json",
                self.temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if stdout:
                results["ruff_results"] = json.loads(stdout)
                results["issues_found"] += len(results["ruff_results"])

            # Run Radon for code metrics
            process = await asyncio.create_subprocess_exec(
                "radon",
                "cc",
                "-j",
                self.temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if stdout:
                results["radon_results"] = json.loads(stdout)
                # Count high complexity functions (score > 10)
                results["issues_found"] += sum(
                    1 for file in results["radon_results"].values()
                    for func in file if func["complexity"] > 10
                )

        return results

    async def _run_security_checks(self, tech_stack: str) -> Dict[str, Any]:
        """Run security checks.
        
        Args:
            tech_stack: Technology stack being used
            
        Returns:
            Dict containing security check results
        """
        results = {
            "bandit_results": [],
            "safety_results": [],
            "vulnerabilities_found": 0
        }

        if tech_stack == "python":
            # Run Bandit for security checks
            process = await asyncio.create_subprocess_exec(
                "bandit",
                "-r",
                "-f",
                "json",
                self.temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if stdout:
                bandit_output = json.loads(stdout)
                results["bandit_results"] = bandit_output["results"]
                results["vulnerabilities_found"] += len(results["bandit_results"])

            # Run Safety for dependency vulnerabilities
            process = await asyncio.create_subprocess_exec(
                "safety",
                "check",
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if stdout:
                results["safety_results"] = json.loads(stdout)
                results["vulnerabilities_found"] += len(results["safety_results"])

        return results

    async def _run_type_checks(self, tech_stack: str) -> Dict[str, Any]:
        """Run type checking.
        
        Args:
            tech_stack: Technology stack being used
            
        Returns:
            Dict containing type check results
        """
        results = {
            "mypy_results": [],
            "type_issues_found": 0,
            "type_coverage": 0.0
        }

        if tech_stack == "python":
            # Run MyPy for type checking
            process = await asyncio.create_subprocess_exec(
                "mypy",
                "--json-report",
                "-",
                self.temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if stdout:
                mypy_output = json.loads(stdout)
                results["mypy_results"] = mypy_output.get("errors", [])
                results["type_issues_found"] = len(results["mypy_results"])

                # Calculate type coverage
                if "coverage" in mypy_output:
                    covered = mypy_output["coverage"]["covered"]
                    total = mypy_output["coverage"]["total"]
                    results["type_coverage"] = (covered / total * 100) if total > 0 else 0.0

        return results

    async def _run_tests(self, tech_stack: str) -> Dict[str, Any]:
        """Run tests with coverage.
        
        Args:
            tech_stack: Technology stack being used
            
        Returns:
            Dict containing test results
        """
        results = {
            "tests_passed": False,
            "coverage_percentage": 0.0,
            "test_output": "",
            "coverage_report": {}
        }

        if tech_stack == "python":
            # Run pytest with coverage
            process = await asyncio.create_subprocess_exec(
                "pytest",
                "--cov=.",
                "--cov-report=json",
                "-v",
                self.temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            results["tests_passed"] = process.returncode == 0
            results["test_output"] = stdout.decode() if stdout else ""

            # Read coverage report
            coverage_file = os.path.join(self.temp_dir, "coverage.json")
            if os.path.exists(coverage_file):
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    results["coverage_report"] = coverage_data
                    results["coverage_percentage"] = coverage_data["totals"]["percent_covered"]

        return results

    async def _run_integration_tests(self, tech_stack: str, container_url: Optional[str] = None) -> Dict[str, Any]:
        """Run integration tests against running container.
        
        Args:
            tech_stack: Technology stack being used
            container_url: URL of the running container to test against
            
        Returns:
            Dict containing integration test results
        """
        results = {
            "integration_tests_passed": False,
            "api_tests_passed": False,
            "database_tests_passed": False,
            "test_output": ""
        }

        if tech_stack == "python":
            # Set container URL environment variable if provided
            env = os.environ.copy()
            if container_url:
                env["TEST_CONTAINER_URL"] = container_url

            # Run integration tests
            process = await asyncio.create_subprocess_exec(
                "pytest",
                "tests/integration",
                "-v",
                cwd=self.temp_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            results["integration_tests_passed"] = process.returncode == 0
            results["test_output"] = stdout.decode() if stdout else ""

            # Parse test output for specific test categories
            if stdout:
                output = stdout.decode()
                results["api_tests_passed"] = "api_test.py ..." in output and "FAILED" not in output
                results["database_tests_passed"] = "db_test.py ..." in output and "FAILED" not in output

        return results

    async def _run_performance_checks(self, tech_stack: str, container_url: Optional[str] = None) -> Dict[str, Any]:
        """Run performance checks.
        
        Args:
            tech_stack: Technology stack being used
            container_url: URL of the running container to test against
            
        Returns:
            Dict containing performance check results
        """
        results = {
            "load_test_results": {},
            "resource_usage": {},
            "performance_issues": []
        }

        if tech_stack == "python" and container_url:
            # Run k6 load test
            load_test_script = """
                import http from 'k6/http';
                import { check } from 'k6';
                
                export default function() {
                    const res = http.get('${CONTAINER_URL}');
                    check(res, {
                        'status is 200': (r) => r.status === 200,
                        'response time < 200ms': (r) => r.timings.duration < 200
                    });
                }
            """
            
            with tempfile.NamedTemporaryFile(suffix='.js', mode='w') as f:
                f.write(load_test_script.replace("${CONTAINER_URL}", container_url))
                f.flush()

                process = await asyncio.create_subprocess_exec(
                    "k6",
                    "run",
                    "--out",
                    "json=" + os.path.join(self.temp_dir, "k6-results.json"),
                    f.name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()

            # Read k6 results
            k6_results_file = os.path.join(self.temp_dir, "k6-results.json")
            if os.path.exists(k6_results_file):
                with open(k6_results_file) as f:
                    results["load_test_results"] = json.load(f)

            # Monitor resource usage
            if self.container:
                stats = self.container.stats(stream=False)
                results["resource_usage"] = {
                    "cpu_usage": stats["cpu_stats"]["cpu_usage"]["total_usage"],
                    "memory_usage": stats["memory_stats"]["usage"],
                    "network_rx": stats["networks"]["eth0"]["rx_bytes"],
                    "network_tx": stats["networks"]["eth0"]["tx_bytes"]
                }

            # Analyze results for issues
            if results["load_test_results"].get("metrics", {}).get("http_req_duration", {}).get("avg", 0) > 200:
                results["performance_issues"].append("High average response time")
            if results["resource_usage"].get("cpu_usage", 0) > 80:
                results["performance_issues"].append("High CPU usage")
            if results["resource_usage"].get("memory_usage", 0) > 500 * 1024 * 1024:  # 500MB
                results["performance_issues"].append("High memory usage")

        return results

    async def validate_implementation(
        self,
        code: Dict[str, str],
        tech_stack: str,
        entry_point: str
    ) -> Dict[str, Any]:
        """Validate implementation with enhanced checks.
        
        Args:
            code: Dictionary of file paths and their contents
            tech_stack: Technology stack being used
            entry_point: The entry point file/module
            
        Returns:
            Dict containing validation results
        """
        try:
            # Write code files
            for file_path, content in code.items():
                full_path = os.path.join(self.temp_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)
                    
            # Run static analysis
            static_analysis = await self._run_static_analysis(tech_stack)
            
            # Run security checks
            security_checks = await self._run_security_checks(tech_stack)
            
            # Run type checks
            type_checks = await self._run_type_checks(tech_stack)
            
            # Run tests with coverage
            test_results = await self._run_tests(tech_stack)
            
            # Create Docker container for runtime validation
            container = await self._create_validation_container(tech_stack, entry_point)
            
            # Run integration tests
            integration_results = await self._run_integration_tests(
                tech_stack,
                f"http://localhost:{container['port']}"
            )
            
            # Run performance checks
            performance_results = await self._run_performance_checks(
                tech_stack,
                f"http://localhost:{container['port']}"
            )
            
            # Aggregate results
            validation_passed = all([
                static_analysis["issues_found"] == 0,
                security_checks["vulnerabilities_found"] == 0,
                type_checks["type_coverage"] >= 80.0,
                test_results["tests_passed"],
                test_results["coverage_percentage"] >= 80.0,
                integration_results["integration_tests_passed"],
                len(performance_results["performance_issues"]) == 0
            ])
            
            return {
                "valid": validation_passed,
                "static_analysis": static_analysis,
                "security_checks": security_checks,
                "type_checks": type_checks,
                "test_results": test_results,
                "integration_results": integration_results,
                "performance_results": performance_results
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return {
                "valid": False,
                "error": str(e)
            }
        finally:
            await self.cleanup()

    async def _create_validation_container(self, tech_stack: str, entry_point: str) -> Dict[str, Any]:
        """Create Docker container for validation.
        
        Args:
            tech_stack: Technology stack being used
            entry_point: The entry point file/module
            
        Returns:
            Dict containing container details
        """
        # Generate Dockerfile
        dockerfile_content = await self._generate_dockerfile(tech_stack, entry_point)
        dockerfile_path = os.path.join(self.temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Build image
        image, _ = self.docker_client.images.build(
            path=self.temp_dir,
            dockerfile="Dockerfile",
            rm=True
        )

        # Run container
        self.container = self.docker_client.containers.run(
            image.id,
            detach=True,
            ports={'8000/tcp': None},
            remove=True
        )

        # Wait for container to be ready
        container_ready = await self._check_container_startup()
        if not container_ready:
            raise Exception("Container failed to start")

        # Get assigned port
        container_info = self.docker_client.api.inspect_container(self.container.id)
        port = container_info['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort']

        return {
            "container_id": self.container.id,
            "port": port
        }

    async def _generate_dockerfile(self, tech_stack: str, entry_point: str) -> str:
        """Generate Dockerfile based on tech stack.
        
        Args:
            tech_stack: Technology stack being used
            entry_point: The entry point file/module
            
        Returns:
            str: Dockerfile content
        """
        if tech_stack == "python":
            return f"""
                FROM python:3.11-slim
                
                WORKDIR /app
                COPY . .
                
                RUN pip install --no-cache-dir -r requirements.txt
                
                EXPOSE 8000
                CMD ["python", "-m", "uvicorn", "{entry_point}:app", "--host", "0.0.0.0", "--port", "8000"]
            """
        elif tech_stack == "node":
            return f"""
                FROM node:18-slim
                
                WORKDIR /app
                COPY . .
                
                RUN npm install
                
                EXPOSE 8000
                CMD ["node", "{entry_point}"]
            """
        else:
            raise ValueError(f"Unsupported tech stack: {tech_stack}")

    async def _check_container_startup(self) -> bool:
        """Check if container started successfully.
        
        Returns:
            bool: True if container is healthy, False otherwise
        """
        retries = 5
        while retries > 0:
            try:
                container_info = self.docker_client.api.inspect_container(self.container.id)
                state = container_info["State"]
                
                if state["Running"]:
                    if "Health" in state:
                        return state["Health"]["Status"] == "healthy"
                    return True
                elif state["ExitCode"] != 0:
                    return False
                    
            except Exception as e:
                logger.error(f"Error checking container status: {str(e)}")
                
            await asyncio.sleep(2)
            retries -= 1
            
        return False 