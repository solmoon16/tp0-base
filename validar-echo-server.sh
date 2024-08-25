#!/usr/bin/bash
received=$(docker run --rm --network=tp0_testing_net busybox sh -c "nc server 12345 && echo $1")
received=$(echo $received | tr -d '\n')
if [[ "$received" == "$1" ]]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi
