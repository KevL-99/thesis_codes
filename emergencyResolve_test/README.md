This folder contains the script used to verify the effects of `emergencyResolve`

To run the script:
1. install Foundry
2. initalize a Foundry project and cd into the directory
    - `forge init <new_project_name>`
    - `cd <new_project_name>`
3. place `Oracle.t.sol` in the `test` folder
4. fork the chain `anvil --fork-url <polygon_node_url>`
5. run test script: `forge test --rpc-url http://127.0.0.1:8545/ --match-path test/Oracle.t.sol -vv`