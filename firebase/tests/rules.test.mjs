// Firestore security rules tests (US-303). Run: npm run test:rules
// Needs Java 21+ (the emulator is a Java program). Each test is one allowed or denied case.

import { readFileSync } from 'node:fs';
import { after, before, beforeEach, describe, test } from 'node:test';
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
} from '@firebase/rules-unit-testing';
import {
  addDoc, collection, doc, getDoc, getDocs, orderBy, query,
  serverTimestamp, setDoc, updateDoc, where,
} from 'firebase/firestore';

let env;

// Signed-in users. Brokers/underwriters carry the custom claim; borrowers have none.
const borrower = () => env.authenticatedContext('aoife', { email: 'aoife@example.com' }).firestore();
const otherBorrower = () => env.authenticatedContext('sean', { email: 'sean@example.com' }).firestore();
const broker = () => env.authenticatedContext('ciaran', { email: 'ciaran@example.com', role: 'broker' }).firestore();
const otherBroker = () => env.authenticatedContext('brokerx', { email: 'x@example.com', role: 'broker' }).firestore();
const underwriter = () => env.authenticatedContext('rachel', { email: 'rachel@example.com', role: 'underwriter' }).firestore();
const anonymous = () => env.unauthenticatedContext().firestore();

before(async () => {
  env = await initializeTestEnvironment({
    projectId: 'demo-al-group11',
    firestore: { rules: readFileSync('firestore.rules', 'utf8') },
  });
});

after(async () => { await env.cleanup(); });

beforeEach(async () => {
  await env.clearFirestore();
  // Seed with rules switched off (as the backend's Admin SDK would write).
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore();
    await setDoc(doc(db, 'applications/AL-2026-0001'), {
      borrowerId: 'aoife', brokerId: 'ciaran', status: 'applied', updatedAt: new Date(),
    });
    await setDoc(doc(db, 'applications/AL-2026-0002'), {
      borrowerId: 'sean', brokerId: 'brokerx', status: 'applied', updatedAt: new Date(),
    });
    await setDoc(doc(db, 'users/aoife'), {
      uid: 'aoife', email: 'aoife@example.com', displayName: 'Aoife', role: 'borrower', createdAt: new Date(),
    });
  });
});

describe('applications: read', () => {
  test('anonymous cannot read', () => assertFails(getDoc(doc(anonymous(), 'applications/AL-2026-0001'))));
  test('borrower reads own', () => assertSucceeds(getDoc(doc(borrower(), 'applications/AL-2026-0001'))));
  test('borrower cannot read another borrower', () => assertFails(getDoc(doc(borrower(), 'applications/AL-2026-0002'))));
  test('broker reads assigned', () => assertSucceeds(getDoc(doc(broker(), 'applications/AL-2026-0001'))));
  test('broker cannot read unassigned', () => assertFails(getDoc(doc(broker(), 'applications/AL-2026-0002'))));
  test('underwriter reads any', () => assertSucceeds(getDoc(doc(underwriter(), 'applications/AL-2026-0002'))));

  test('broker pipeline query WITH brokerId filter works', () =>
    assertSucceeds(getDocs(query(collection(broker(), 'applications'),
      where('brokerId', '==', 'ciaran'), orderBy('updatedAt', 'desc')))));
  test('broker query WITHOUT filter is rejected', () =>
    assertFails(getDocs(collection(broker(), 'applications'))));
  test('underwriter can list all', () =>
    assertSucceeds(getDocs(query(collection(underwriter(), 'applications'), orderBy('updatedAt', 'desc')))));
  test('borrower list query with own filter works', () =>
    assertSucceeds(getDocs(query(collection(borrower(), 'applications'), where('borrowerId', '==', 'aoife')))));
});

describe('applications: no client writes (backend only)', () => {
  test('borrower cannot create', () =>
    assertFails(setDoc(doc(borrower(), 'applications/AL-2026-0003'), { borrowerId: 'aoife', status: 'applied' })));
  test('borrower cannot change own status', () =>
    assertFails(updateDoc(doc(borrower(), 'applications/AL-2026-0001'), { status: 'funded' })));
  test('underwriter cannot change status directly', () =>
    assertFails(updateDoc(doc(underwriter(), 'applications/AL-2026-0001'), { status: 'underwriter_approved' })));
});

describe('users', () => {
  const profile = (overrides = {}) => ({
    uid: 'newbie', email: 'newbie@example.com', displayName: 'New', role: 'borrower',
    createdAt: serverTimestamp(), ...overrides,
  });
  const newbie = (claims = {}) =>
    env.authenticatedContext('newbie', { email: 'newbie@example.com', ...claims }).firestore();

  test('borrower creates own profile', () => assertSucceeds(setDoc(doc(newbie(), 'users/newbie'), profile())));
  test('cannot register as underwriter', () =>
    assertFails(setDoc(doc(newbie(), 'users/newbie'), profile({ role: 'underwriter' }))));
  test('cannot create a profile for someone else', () =>
    assertFails(setDoc(doc(newbie(), 'users/other'), profile({ uid: 'other' }))));
  test('cannot add extra fields', () =>
    assertFails(setDoc(doc(newbie(), 'users/newbie'), profile({ isAdmin: true }))));
  test('cannot change own role later', () =>
    assertFails(updateDoc(doc(borrower(), 'users/aoife'), { role: 'underwriter' })));
  test('can change own display name', () =>
    assertSucceeds(updateDoc(doc(borrower(), 'users/aoife'), { displayName: 'Aoife B.' })));
  test('cannot read another user profile', () => assertFails(getDoc(doc(otherBorrower(), 'users/aoife'))));
  test('underwriter can read profiles', () => assertSucceeds(getDoc(doc(underwriter(), 'users/aoife'))));
});

describe('messages (subcollection of an application)', () => {
  const msg = (overrides = {}) => ({
    senderId: 'aoife', senderRole: 'borrower', text: 'Hello', sentAt: serverTimestamp(), ...overrides,
  });
  test('borrower writes on own application', () =>
    assertSucceeds(addDoc(collection(borrower(), 'applications/AL-2026-0001/messages'), msg())));
  test('borrower cannot write on another application', () =>
    assertFails(addDoc(collection(borrower(), 'applications/AL-2026-0002/messages'), msg())));
  test('cannot pretend to be someone else', () =>
    assertFails(addDoc(collection(borrower(), 'applications/AL-2026-0001/messages'), msg({ senderId: 'ciaran' }))));
  test('assigned broker can read thread', () =>
    assertSucceeds(getDocs(collection(broker(), 'applications/AL-2026-0001/messages'))));
  test('other broker cannot read thread', () =>
    assertFails(getDocs(collection(otherBroker(), 'applications/AL-2026-0001/messages'))));
});

describe('backend-only collections', () => {
  test('client cannot write valuations', () =>
    assertFails(setDoc(doc(borrower(), 'valuations/v1'), { requestedBy: 'aoife', estimate: 1 })));
  test('client cannot write payments', () =>
    assertFails(setDoc(doc(borrower(), 'payments/p1'), { borrowerId: 'aoife', status: 'paid' })));
  test('client cannot touch counters', () =>
    assertFails(getDoc(doc(underwriter(), 'counters/applications-2026'))));
});

describe('reviews', () => {
  const review = (rating) => ({ borrowerId: 'aoife', rating, createdAt: serverTimestamp() });
  test('rating 5 accepted', () => assertSucceeds(addDoc(collection(borrower(), 'reviews'), review(5))));
  test('rating 6 rejected', () => assertFails(addDoc(collection(borrower(), 'reviews'), review(6))));
  test('broker cannot leave a review', () =>
    assertFails(addDoc(collection(broker(), 'reviews'), { ...review(4), borrowerId: 'ciaran' })));
});
