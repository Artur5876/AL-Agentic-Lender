// Deploy LoanNote to the local anvil chain (docker-compose service, chainId 31337).
//   docker compose up anvil          (or the whole stack)
//   cd contracts && npm run deploy:local
//
// Writes deployments/local.json (address + ABI) for the backend (Step 4, backend/app/chain.py).
// That file is git-ignored: every fresh chain gives a new address.
//
// Environment (all optional):
//   AL_CHAIN_RPC_URL         default http://127.0.0.1:8545
//   AL_CHAIN_DEPLOYER_KEY    deployer private key; default = the node's first unlocked dev account
//   AL_CHAIN_MINTER_ADDRESS  address that gets MINTER_ROLE (the backend signer); default = deployer
const fs = require("node:fs");
const path = require("node:path");
const hre = require("hardhat");

async function main() {
  const { ethers, network } = hre;
  const [deployer] = await ethers.getSigners();
  const chainId = Number((await ethers.provider.getNetwork()).chainId);
  if (chainId !== 31337) {
    throw new Error(`Refusing to deploy: chainId ${chainId} is not the local chain (31337).`);
  }

  const note = await ethers.deployContract("LoanNote", [deployer.address]);
  await note.waitForDeployment();
  const address = await note.getAddress();
  const receipt = await note.deploymentTransaction().wait();

  const minter = process.env.AL_CHAIN_MINTER_ADDRESS || deployer.address;
  if (!ethers.isAddress(minter)) throw new Error(`AL_CHAIN_MINTER_ADDRESS is not an address`);
  await (await note.grantRole(await note.MINTER_ROLE(), minter)).wait();

  const artifact = await hre.artifacts.readArtifact("LoanNote");
  const out = {
    contract: "LoanNote",
    network: network.name,
    chainId,
    address,
    deployer: deployer.address,
    minter,
    blockNumber: receipt.blockNumber,
    deployedAt: new Date().toISOString(),
    abi: artifact.abi,
  };
  const file = path.join(__dirname, "..", "deployments", "local.json");
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(out, null, 2) + "\n");

  console.log(`LoanNote deployed at ${address} (chainId ${chainId}, block ${receipt.blockNumber})`);
  console.log(`MINTER_ROLE granted to ${minter}`);
  console.log(`Wrote ${path.relative(process.cwd(), file)}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
