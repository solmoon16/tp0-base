#!/usr/bin/bash
message='holis'
received=$(docker run --rm --network=tp0_testing_net busybox sh -c "nc server 12345 && echo $message")
if [ $received == $message ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi
