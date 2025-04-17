// SPDX-License-Identifier: MIT
// Fork chain using anvil: anvil --fork-url https://polygon-mainnet.g.alchemy.com/v2/R4Ac51ZNN8CX3E4Z4CJoqIcpYqBZIzvM
// Run test script: forge test --rpc-url http://127.0.0.1:8545/ --match-path test/Oracle.t.sol -vv
pragma solidity 0.8.15;

import {Test, console, Vm} from "forge-std/Test.sol";


interface IUmaCtfAdapter {
    function flag(bytes32 questionID) external;
    function emergencyResolve(bytes32 questionID, uint256[] calldata payouts) external;
}

contract EmergencyResolveTest is Test {
    IUmaCtfAdapter oracle;
    address admin = 0x3dcE0a29139A851Da1dFCa56Af8e8a6440b4D952;
    address oracleAddress = 0x6A9D222616C90FcA5754cd1333cFD9b7fb6a4F74;
    function setUp() public {
        oracle = IUmaCtfAdapter(oracleAddress); 
        // Impersonate the admin account
        vm.startPrank(admin);
    }

    function testEmergencyResolve() public {
        vm.recordLogs();
        // replace this with the question ID of any yes/no question on Polymarket
        bytes32 questionID = 0x70b1b7609e431c2d11da5c30326231ed715c47ee070f0088590bbed685fbb977;
        oracle.flag(questionID);
        console.log(block.timestamp);
        skip(216000);
        console.log(block.timestamp);
        // setting payouts to an arbitrary answer
        uint256[] memory t = new uint256[](2);
        t[0] = 1;
        t[1] = 0; 
        oracle.emergencyResolve(questionID, t);
        Vm.Log[] memory entries = vm.getRecordedLogs();
        assertEq(entries.length, 3); 
        assertEq(entries[2].topics[0], keccak256("QuestionEmergencyResolved(bytes32,uint256[])"));
        vm.stopPrank();
    }
}