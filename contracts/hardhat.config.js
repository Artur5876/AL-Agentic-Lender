// Hardhat 2 config for the AL contracts (US-321/322/331).
// `npx hardhat test` uses the in-process Hardhat network (no node needed).
// `npm run deploy:local` deploys to the anvil node from docker-compose.yml.
require("@nomicfoundation/hardhat-chai-matchers");
require("@nomicfoundation/hardhat-ethers");

// Optional: a deployer key from the environment (never commit it). Without it, the
// anvil node's own unlocked dev accounts are used, so no key is needed locally.
const deployerKey = process.env.AL_CHAIN_DEPLOYER_KEY;

module.exports = {
  solidity: {
    version: "0.8.28",
    settings: { optimizer: { enabled: true, runs: 200 }, evmVersion: "cancun" },
  },
  networks: {
    anvil: {
      url: process.env.AL_CHAIN_RPC_URL || "http://127.0.0.1:8545",
      chainId: 31337,
      ...(deployerKey ? { accounts: [deployerKey] } : {}),
    },
  },
};
