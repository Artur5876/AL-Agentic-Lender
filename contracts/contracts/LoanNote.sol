// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";

/// @title AL loan note (US-321, US-322) with audit hash (US-331)
/// @notice One NFT per approved loan. Stores only loan terms and a PSEUDONYMOUS borrower
///         reference (bytes32 = SHA-256 of borrowerId + secret salt, computed off-chain).
///         No names, emails, addresses or other personal data are ever stored on-chain.
/// @dev Only accounts with MINTER_ROLE (the AL backend's signer) can mint.
///      recordAudit stores the SHA-256 of the canonical decision record (backend/app/audit.py)
///      once per token, so any later change to the off-chain record can be detected.
///      Academic prototype on a local chain; not a real financial instrument.
contract LoanNote is ERC721, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    /// Lifecycle of the note on-chain. Only Minted is set in Sprint 2 (US-323 adds the rest).
    enum LoanStatus {
        Minted,
        Funded,
        Closed
    }

    struct Loan {
        uint256 principalCents; // loan amount in euro cents (integers only on-chain)
        uint16 aprBps; // annual rate in basis points, 390 = 3.90%
        uint8 termYears;
        LoanStatus status;
        bytes32 borrowerRef; // pseudonymous, see contract notice
    }

    event LoanMinted(
        uint256 indexed tokenId,
        address indexed to,
        bytes32 indexed borrowerRef,
        uint256 principalCents,
        uint16 aprBps,
        uint8 termYears
    );

    event AuditRecorded(uint256 indexed tokenId, bytes32 auditHash);

    error InvalidLoanTerms();
    error EmptyAuditHash();
    error AuditAlreadyRecorded(uint256 tokenId);

    uint256 private _nextTokenId = 1;
    mapping(uint256 tokenId => Loan) private _loans;
    mapping(uint256 tokenId => bytes32) private _auditHashes;

    /// @param admin gets DEFAULT_ADMIN_ROLE and can grant or revoke MINTER_ROLE.
    constructor(address admin) ERC721("AL Loan Note", "ALLN") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /// @notice Mint a loan note to `to` (the bank's own address in AL).
    /// @return tokenId the new token's ID (starts at 1, increases by 1).
    function mint(
        address to,
        uint256 principalCents,
        uint16 aprBps,
        uint8 termYears,
        bytes32 borrowerRef
    ) external onlyRole(MINTER_ROLE) returns (uint256 tokenId) {
        if (principalCents == 0 || termYears == 0 || borrowerRef == bytes32(0)) {
            revert InvalidLoanTerms();
        }
        tokenId = _nextTokenId++;
        _loans[tokenId] = Loan(principalCents, aprBps, termYears, LoanStatus.Minted, borrowerRef);
        _safeMint(to, tokenId);
        emit LoanMinted(tokenId, to, borrowerRef, principalCents, aprBps, termYears);
    }

    /// @notice Read a loan note. Reverts with ERC721NonexistentToken for unknown IDs.
    function getLoan(uint256 tokenId) external view returns (Loan memory) {
        _requireOwned(tokenId);
        return _loans[tokenId];
    }

    /// @notice Store the audit hash of a loan's decision record. Write-once per token.
    function recordAudit(uint256 tokenId, bytes32 auditHash) external onlyRole(MINTER_ROLE) {
        _requireOwned(tokenId);
        if (auditHash == bytes32(0)) revert EmptyAuditHash();
        if (_auditHashes[tokenId] != bytes32(0)) revert AuditAlreadyRecorded(tokenId);
        _auditHashes[tokenId] = auditHash;
        emit AuditRecorded(tokenId, auditHash);
    }

    /// @notice The stored audit hash, or bytes32(0) if none recorded yet.
    ///         Reverts with ERC721NonexistentToken for unknown IDs.
    function getAuditHash(uint256 tokenId) external view returns (bytes32) {
        _requireOwned(tokenId);
        return _auditHashes[tokenId];
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
