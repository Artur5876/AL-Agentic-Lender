// US-321 / US-322: LoanNote minting, reading and access control.
const { expect } = require("chai");
const { ethers } = require("hardhat");

// Synthetic test data only. borrowerRef is a hash, never personal data.
const REF = ethers.sha256(ethers.toUtf8Bytes("borrower-aoife" + "test-salt"));
const LOAN = { principalCents: 33_500_000n, aprBps: 390, termYears: 30 };
const MINTED = 0n; // LoanStatus.Minted

describe("LoanNote", function () {
  let note, admin, minter, bank, stranger, MINTER_ROLE, ADMIN_ROLE;

  beforeEach(async function () {
    [admin, minter, bank, stranger] = await ethers.getSigners();
    note = await ethers.deployContract("LoanNote", [admin.address]);
    MINTER_ROLE = await note.MINTER_ROLE();
    ADMIN_ROLE = await note.DEFAULT_ADMIN_ROLE();
    await note.connect(admin).grantRole(MINTER_ROLE, minter.address);
  });

  const mint = (signer = minter, l = LOAN, ref = REF) =>
    note.connect(signer).mint(bank.address, l.principalCents, l.aprBps, l.termYears, ref);

  describe("deployment", function () {
    it("has name, symbol and the admin role", async function () {
      expect(await note.name()).to.equal("AL Loan Note");
      expect(await note.symbol()).to.equal("ALLN");
      expect(await note.hasRole(ADMIN_ROLE, admin.address)).to.be.true;
      expect(MINTER_ROLE).to.equal(ethers.id("MINTER_ROLE"));
    });

    it("supports ERC-721, AccessControl and ERC-165 interfaces", async function () {
      expect(await note.supportsInterface("0x80ac58cd")).to.be.true; // ERC721
      expect(await note.supportsInterface("0x7965db0b")).to.be.true; // IAccessControl
      expect(await note.supportsInterface("0x01ffc9a7")).to.be.true; // ERC165
      expect(await note.supportsInterface("0xffffffff")).to.be.false;
    });
  });

  describe("mint and read (US-321)", function () {
    it("stores every field and reads it back", async function () {
      await mint();
      const loan = await note.getLoan(1);
      expect(loan.principalCents).to.equal(LOAN.principalCents);
      expect(loan.aprBps).to.equal(LOAN.aprBps);
      expect(loan.termYears).to.equal(LOAN.termYears);
      expect(loan.status).to.equal(MINTED);
      expect(loan.borrowerRef).to.equal(REF);
      expect(await note.ownerOf(1)).to.equal(bank.address);
      expect(await note.balanceOf(bank.address)).to.equal(1n);
    });

    it("emits LoanMinted and returns sequential token IDs", async function () {
      await expect(mint())
        .to.emit(note, "LoanMinted")
        .withArgs(1n, bank.address, REF, LOAN.principalCents, LOAN.aprBps, LOAN.termYears);
      expect(await note.connect(minter).mint.staticCall(
        bank.address, 1n, 400, 25, REF)).to.equal(2n);
      await mint();
      expect(await note.ownerOf(2)).to.equal(bank.address);
    });

    it("stores the maximum values without overflow", async function () {
      const max = { principalCents: ethers.MaxUint256, aprBps: 65535, termYears: 255 };
      await mint(minter, max);
      const loan = await note.getLoan(1);
      expect(loan.principalCents).to.equal(ethers.MaxUint256);
      expect(loan.aprBps).to.equal(65535n);
      expect(loan.termYears).to.equal(255n);
    });

    it("rejects zero principal, zero term or an empty borrower reference", async function () {
      await expect(mint(minter, { ...LOAN, principalCents: 0n }))
        .to.be.revertedWithCustomError(note, "InvalidLoanTerms");
      await expect(mint(minter, { ...LOAN, termYears: 0 }))
        .to.be.revertedWithCustomError(note, "InvalidLoanTerms");
      await expect(mint(minter, LOAN, ethers.ZeroHash))
        .to.be.revertedWithCustomError(note, "InvalidLoanTerms");
    });

    it("reverts when reading a token that does not exist", async function () {
      await expect(note.getLoan(99))
        .to.be.revertedWithCustomError(note, "ERC721NonexistentToken")
        .withArgs(99n);
    });
  });

  describe("access control (US-322)", function () {
    it("a mint from an address without MINTER_ROLE fails", async function () {
      await expect(mint(stranger))
        .to.be.revertedWithCustomError(note, "AccessControlUnauthorizedAccount")
        .withArgs(stranger.address, MINTER_ROLE);
    });

    it("even the admin cannot mint without MINTER_ROLE", async function () {
      await expect(mint(admin))
        .to.be.revertedWithCustomError(note, "AccessControlUnauthorizedAccount")
        .withArgs(admin.address, MINTER_ROLE);
    });

    it("the admin can grant MINTER_ROLE, and the new minter can mint", async function () {
      await expect(note.connect(admin).grantRole(MINTER_ROLE, stranger.address))
        .to.emit(note, "RoleGranted")
        .withArgs(MINTER_ROLE, stranger.address, admin.address);
      await expect(mint(stranger)).to.emit(note, "LoanMinted");
    });

    it("a non-admin cannot grant MINTER_ROLE", async function () {
      await expect(note.connect(stranger).grantRole(MINTER_ROLE, stranger.address))
        .to.be.revertedWithCustomError(note, "AccessControlUnauthorizedAccount")
        .withArgs(stranger.address, ADMIN_ROLE);
    });

    it("a revoked minter can no longer mint", async function () {
      await note.connect(admin).revokeRole(MINTER_ROLE, minter.address);
      await expect(mint())
        .to.be.revertedWithCustomError(note, "AccessControlUnauthorizedAccount");
    });
  });
});
