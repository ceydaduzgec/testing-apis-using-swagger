#!/usr/bin/env bash

CONTAINER_UID=$(id -u) CONTAINER_GID=$(id -g) docker-compose -f docker-compose.yml exec app bash
