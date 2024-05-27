# Description
Simulation of small distributed system (centralized and decentralized). 
- Execute test: run eval/eval.py
- Execute Centralized server and client: run Centralized.py and CentralizedClient.py
- Execute Decentralized server and client: run Decentralized.py and DecentralizedClient.py


# Distributed storage systems and the CAP theorem

```
Project/
│
├── proto/
│   ├── store.proto
│   ├── store_pb2.py
│   └── store_pb2_grpc.py
│
├── config_centralized.yaml
├── config_descentralized.yaml
├── centralized.py
├── decentralized.py
│
├── eval/
│   ├── test_centralized_system.py
│   └── test_decentralized_system.py
│
├── Centralized/
│   ├── Master.py
│   └── Slave.py
│
├── CentralizedSaves/
│   └── <slave_X_ip>-<slave_X_port>.txt
│
├── Decentralized/
│   └── Node.py
│
└── DecentralizedSaves/
    └── <node_X_ip>-<node_X_port>.txt
```

## Directory Structure Explanation

- **proto/**: Contains Protocol Buffer files used for defining gRPC services and messages. Generated Python files (`store_pb2.py` and `store_pb2_grpc.py`) based on `store.proto` should be stored here.

- **centralized_config.yaml and decentralized_config.yaml**: YAML configuration files containing settings for the centralized and decentralized systems.

- **eval/**: Directory containing evaluation scripts and tests.

  - **test_centralized_system.py**: Script containing unit tests for the centralized system.

    - ***Sample***: 

    ```
    master:
      ip: <IP>
      port: <Port>

    slaves:
      - ip: <slave_1_IP>
        port: <slave_1_Port>
      - ip: <slave_2_IP>
        port: <slave_2_Port>
      ...
      ```
  
  - **test_decentralized_system.py**: Script containing unit tests for the decentralized system.

      - ***Sample***: 

    ```
    nodes:
      - ip: <node_1_IP>
        port: <node_1_Port>
        weight: <node_1_Weight>
      - ip: <node_2_IP>
        port: <node_2_Port>
        weight: <node_2_Weight>
      ...
      ```

- **Centralized**: Folder containing Master and Slave scripts for centralized system

- **Dentralized**: Folder containing Node script for decentralized system.

- **CentralizedSaves and DecentralizedSaves**: Folder containing backup files in case of total server failure.


Each component of the project is organized into its respective directory, facilitating clear separation of concerns and ease of navigation. The `eval` directory specifically houses test scripts for evaluating the functionality and correctness of the implemented systems.

> **Note:** Students are required to define the necessary stubs for implementing the Two Phase Commit (2PC) protocol and for node registration in the system. These stubs must be manually added to the store.proto file by the students as part of their implementation.

