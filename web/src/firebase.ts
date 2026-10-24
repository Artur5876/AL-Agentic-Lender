import { getApp, getApps, initializeApp } from "firebase/app";
import { connectAuthEmulator, getAuth } from "firebase/auth";
import { connectFirestoreEmulator, getFirestore } from "firebase/firestore";

// Local emulator project (see docker-compose.yml: AL_FIREBASE_PROJECT_ID).
// No real keys are needed for the emulators. Never commit real keys.
const app = getApps().length
  ? getApp()
  : initializeApp({ projectId: "demo-al-group11", apiKey: "demo-key" });

export const auth = getAuth(app);
export const db = getFirestore(app);

if (import.meta.env.DEV) {
  try {
    connectAuthEmulator(auth, "http://localhost:9099", { disableWarnings: true });
    connectFirestoreEmulator(db, "localhost", 8080);
  } catch {
    // Vite hot reload can run this twice; connecting twice throws, which is safe to ignore.
  }
}
