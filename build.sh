cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
make -j
./ramulator2 -f exp_configs/ordered_test_config.yaml
