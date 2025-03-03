# Testing GitHub Actions Workflows

This document provides instructions on how to test GitHub Actions workflows locally without having to push changes to the repository.

## Option 1: Manual Trigger in GitHub UI

With the `workflow_dispatch` trigger added to the workflow, you can manually trigger the workflow from the GitHub UI:

1. Go to your GitHub repository
2. Click on the "Actions" tab
3. Select the "Services Pipeline" workflow from the left sidebar
4. Click the "Run workflow" button
5. Select the branch you want to run the workflow on
6. Configure the input parameters:
   - Debug enabled: Enable debug logging
   - Test only: Run only the test job
   - Build only: Run only up to the build job (no deployment)
7. Click "Run workflow"

## Option 2: Local Testing with Act

You can test GitHub Actions workflows locally using [act](https://github.com/nektos/act), a tool that runs GitHub Actions locally using Docker.

### Prerequisites

1. Install [act](https://github.com/nektos/act#installation)
2. Docker installed and running

### Using the Test Script

We've provided a script to simplify testing with act:

```bash
./test-workflow.sh [options]
```

Options:
- `-e, --event EVENT`: Event to trigger (default: workflow_dispatch)
- `-d, --debug`: Enable debug mode
- `-t, --test-only`: Run only the test job
- `-b, --build-only`: Run only up to the build job (no deployment)
- `-s, --secrets FILE`: Path to secrets file (default: .secrets)
- `-h, --help`: Show help message

### Examples

Run the entire workflow with workflow_dispatch event:
```bash
./test-workflow.sh
```

Run only the test job:
```bash
./test-workflow.sh --test-only
```

Run with debug logging enabled:
```bash
./test-workflow.sh --debug
```

Run with a specific event:
```bash
./test-workflow.sh --event pull_request
```

## Option 3: Testing Docker Build Only

If you only want to test the Docker build part of the workflow, you can use the provided script:

```bash
./test-docker-build.sh [options]
```

Options:
- `-s, --service SERVICE`: Service to build (default: base)
- `-p, --push`: Push the image to registry
- `-r, --registry REGISTRY`: Docker registry (default: ghcr.io)
- `-o, --owner OWNER`: Owner/organization (default: git username or 'local')
- `-t, --tag TAG`: Image tag (default: test)
- `--repo REPO`: Repository name (default: cahoots)
- `-h, --help`: Show help message

### Examples

Build the base image:
```bash
./test-docker-build.sh
```

Build a specific service:
```bash
./test-docker-build.sh --service master
```

Build and push an image:
```bash
./test-docker-build.sh --service developer --push
```

## Troubleshooting

### GitHub Container Registry Authentication

If you encounter authentication issues with GitHub Container Registry:

1. Create a Personal Access Token (PAT) with `write:packages` scope
2. Add it to your secrets file as `CR_PAT`
3. Login to GitHub Container Registry:
   ```bash
   echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin
   ```

### Act Limitations

- Act may not perfectly simulate all GitHub Actions environments
- Some actions might not work as expected locally
- For complex workflows, testing in GitHub's environment might still be necessary

## Notes

- The workflow has been configured to allow manual triggering and selective job execution
- Debug logging can be enabled to help troubleshoot issues
- The workflow will only deploy to staging and production when triggered from the main branch 