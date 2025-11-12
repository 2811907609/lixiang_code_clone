#!/bin/bash

set -e

# Configuration
IMAGE_NAME="ai-agent-builder"
CONTAINER_NAME="ai-builder-$$"
OUTPUT_DIR="./agent-workspace"
DOCKERFILE_PATH="deploy/Dockerfile-agent-tars"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if output directory exists, create if not
if [ ! -d "$OUTPUT_DIR" ]; then
    log_info "Creating output directory: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

# Check if tar files already exist
TAR_FILES=("ai-mono-repo.tar" "uv.tar" "uv_shared.tar")
ALL_EXIST=true

for tar_file in "${TAR_FILES[@]}"; do
    if [ ! -f "$OUTPUT_DIR/$tar_file" ]; then
        ALL_EXIST=false
        break
    fi
done

if [ "$ALL_EXIST" = true ]; then
    log_warn "Found existing tar files in $OUTPUT_DIR. Use --force to rebuild."
    echo "Existing files:"
    for tar_file in "${TAR_FILES[@]}"; do
        echo "  - $OUTPUT_DIR/$tar_file"
    done

    if [ "$1" != "--force" ]; then
        log_info "Skipping build. Use '$0 --force' to rebuild."
        exit 0
    else
        log_info "Force rebuild requested, removing existing files..."
        for tar_file in "${TAR_FILES[@]}"; do
            rm -f "$OUTPUT_DIR/$tar_file"
        done
    fi
fi

# Build Docker image
log_info "Building Docker image: $IMAGE_NAME"
docker build --progress plain -f "$DOCKERFILE_PATH" -t "$IMAGE_NAME" ../../

# Create and run container
log_info "Creating container: $CONTAINER_NAME"
docker create --name "$CONTAINER_NAME" "$IMAGE_NAME"

# Extract tar files from container
log_info "Extracting tar files..."
for tar_file in "${TAR_FILES[@]}"; do
    log_info "Copying $tar_file..."
    docker cp "$CONTAINER_NAME:/output/$tar_file" "$OUTPUT_DIR/$tar_file"
done

# Cleanup
log_info "Cleaning up container: $CONTAINER_NAME"
docker rm "$CONTAINER_NAME"

# Verify extracted files
log_info "Verifying extracted files..."
for tar_file in "${TAR_FILES[@]}"; do
    if [ -f "$OUTPUT_DIR/$tar_file" ]; then
        size=$(ls -lh "$OUTPUT_DIR/$tar_file" | awk '{print $5}')
        log_info "✓ $tar_file ($size)"
    else
        log_error "✗ $tar_file not found!"
        exit 1
    fi
done

log_info "Build completed successfully!"
log_info "Artifacts saved to: $OUTPUT_DIR"
echo
echo "Generated files:"
for tar_file in "${TAR_FILES[@]}"; do
    echo "  - $OUTPUT_DIR/$tar_file"
done
