#!/usr/bin/env bash
set -ue

#
# This script prepare the environment for running the Hub.
# Preparation consists of:
# - Pull-or-build JupyterHub (server) image
# - Pull-or-build Notebook (client) images
#

HERE=$(dirname `realpath "$0"`)

SERVICE_IMAGE_LIST="${HERE}/config/imagelist"
TOBUILD_IMAGE_LIST="imagelist"

function pull_notebook_images() {
    #
    # Pull images from file './config/imageslist'
    #
    [ ! -f "$SERVICE_IMAGE_LIST" ] \
        && ( echo "File '$SERVICE_IMAGE_LIST' not found"; exit 1; )

    for image in `grep -E -v "^$|#" $SERVICE_IMAGE_LIST`
    do
        echo "Getting image '$image'.."
        docker pull $image
        [ $? ] && echo "..done" || echo "..failed"
    done
}

function build_notebook_images() {
    #
    # Build images from file 'TOBUILD_IMAGE_LIST'.
    # Overwrite file 'SERVICE_IMAGE_LIST'.
    #
    # Name of images in SERVICE_IMAGE_LIST will be that of
    # TOBUILD_IMAGE_LIST without the (probable) user/org namespace prefix,
    # eg, "jupyter/minimal-notebook" to "minimal-notebook"
    #
    [ ! -f "$TOBUILD_IMAGE_LIST" ] \
        && ( echo "File '$TOBUILD_IMAGE_LIST' not found."; exit 1; )

    DOCKERFILE="./dockerfiles/singleuser.dockerfile"
    CONTEXT=`dirname $DOCKERFILE`

    for SRC_IMAGE in `grep -E -v "^$|#" $TOBUILD_IMAGE_LIST`
    do
        DST_IMAGE="${SRC_IMAGE##*/}"
        echo "Building image '$DST_IMAGE' (from '$SRC_IMAGE').."

        docker build -t $DST_IMAGE \
                    --build-arg BASE_IMAGE="$SRC_IMAGE" \
                     -f $DOCKERFILE $CONTEXT

        [ $? ] \
            && (echo "$DST_IMAGE" >> imagelist.tmp; echo "..done";) \
            || echo "..failed"
    done

    # Overwrite SERVICE_IMAGE_LIST with built image names
    [ -f imagelist.tmp ] && mv imagelist.tmp $SERVICE_IMAGE_LIST
}

# function build_jupyterhub_image() {
#     # Build jupyterhub image
#     docker compose -f ../compose.yml build
# }


# Default values
PULL_NOTEBOOK_IMAGES=false
BUILD_NOTEBOOK_IMAGES=false
# BUILD_JUPYTERHUB_IMAGE=false
QUIET=false

# Function to display script usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -p, --pull_notebook_images   Pull notebook images in '$SERVICE_IMAGE_LIST'"
    echo "  -b, --build_notebook_images  Build notebook images in '$TOBUILD_IMAGE_LIST'"
    echo "                               Update 'config/imagelist' with new ones"
    # echo "  -j, --build_jupyterhub_image Build JupyterHub image"
    echo "  -q, --quiet                  Suppress output from docker"
    echo "  -h, --help                   Display this help message"
    exit 1
}

# If no options are provided, display usage
if [[ "$#" -eq 0 ]]; then
    usage
fi

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--pull-notebook-images)
            PULL_NOTEBOOK_IMAGES=true
            ;;
        -b|--build-notebook-images)
            BUILD_NOTEBOOK_IMAGES=true
            ;;
        # -j|--build_jupyterhub_image)
        #     BUILD_JUPYTERHUB_IMAGE=true
        #     ;;
        -q|--quiet)
            QUIET=true
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Invalid option: $1"
            usage
            ;;
    esac
    shift
done

# Perform actions based on options
if $PULL_NOTEBOOK_IMAGES; then
    # echo "Pulling notebook images..."
    pull_notebook_images
fi

if $BUILD_NOTEBOOK_IMAGES; then
    # echo "Building notebook images..."
    build_notebook_images
fi

# if $BUILD_JUPYTERHUB_IMAGE; then
#     echo "Building JupyterHub image..."
#     build_jupyterhub_image
# fi
