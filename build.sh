#cd py-scripts/
#python random_trace_generator.py
# cd ..
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
make -j
./ramulator2 -f exp_configs/tpch_test_config.yaml
