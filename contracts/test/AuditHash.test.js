// US-331: audit hash stored on-chain, write-once, MINTER_ROLE only.
const { expect } = require("chai");
const { ethers } = require("hardhat");

const REF = ethers.sha256(ethers.toUtf8Bytes("borrower-aoife" + "test-salt"));
// A SHA-256 hex digest as produced by backend/app/audit.py audit_hash() (synthetic record).
const HASH = "0x" + "ab".repeat(32);
const OTHER_HASH = "0x" + "cd".repeat(32);

describe("LoanNote audit hash (US-331)", function () {
  let note, admin, minter, bank, stranger, MINTER_ROLE;

  beforeEach(async function () {
    [admin, minter, bank, stranger] = await ethers.getSigners();
    note = await ethers.deployContract("LoanNote", [admin.address]);
    MINTER_ROLE = await note.MINTER_ROLE();
    await note.connect(admin).grantRole(MINTER_ROLE, minter.address);
    await note.connect(minter).mint(bank.address, 33_500_000n, 390, 30, REF); // token 1
  });

  it("records the hash, emits AuditRecorded and reads it back", async function () {
    expect(await note.getAuditHash(1)).to.equal(ethers.ZeroHash); // nothing yet
    await expect(note.connect(minter).recordAudit(1, HASH))
      .to.emit(note, "AuditRecorded")
      .withArgs(1n, HASH);
    expect(await note.getAuditHash(1)).to.equal(HASH);
  });

  it("accepts the same 64-char hex digest format the backend produces", async function () {
    const digest = ethers.sha256(ethers.toUtf8Bytes('{"a":1}')).slice(2); // hex, no 0x
    await note.connect(minter).recordAudit(1, "0x" + digest);
    expect((await note.getAuditHash(1)).slice(2)).to.equal(digest);
  });

  it("can only be set once: a second call reverts and the hash is unchanged", async function () {
    await note.connect(minter).recordAudit(1, HASH);
    await expect(note.connect(minter).recordAudit(1, OTHER_HASH))
      .to.be.revertedWithCustomError(note, "AuditAlreadyRecorded")
      .withArgs(1n);
    await expect(note.connect(minter).recordAudit(1, HASH))
      .to.be.revertedWithCustomError(note, "AuditAlreadyRecorded");
    expect(await note.getAuditHash(1)).to.equal(HASH);
  });

  it("fails from an address without MINTER_ROLE", async function () {
    await expect(note.connect(stranger).recordAudit(1, HASH))
      .to.be.revertedWithCustomError(note, "AccessControlUnauthorizedAccount")
      .withArgs(stranger.address, MINTER_ROLE);
    // The token owner (bank) has no special right either.
    await expect(note.connect(bank).recordAudit(1, HASH))
      .to.be.revertedWithCustomError(note, "AccessControlUnauthorizedAccount");
  });

  it("requires the token to exist", async function () {
    await expect(note.connect(minter).recordAudit(99, HASH))
      .to.be.revertedWithCustomError(note, "ERC721NonexistentToken")
      .withArgs(99n);
    await expect(note.getAuditHash(99))
      .to.be.revertedWithCustomError(note, "ERC721NonexistentToken")
      .withArgs(99n);
  });

  it("rejects an empty (zero) hash", async function () {
    await expect(note.connect(minter).recordAudit(1, ethers.ZeroHash))
      .to.be.revertedWithCustomError(note, "EmptyAuditHash");
  });

  it("keeps hashes separate per token", async function () {
    await note.connect(minter).mint(bank.address, 1n, 390, 25, REF); // token 2
    await note.connect(minter).recordAudit(1, HASH);
    await note.connect(minter).recordAudit(2, OTHER_HASH);
    expect(await note.getAuditHash(1)).to.equal(HASH);
    expect(await note.getAuditHash(2)).to.equal(OTHER_HASH);
  });
});
