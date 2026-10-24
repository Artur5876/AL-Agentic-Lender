package ie.mtu.agenticlender.firebase

import android.content.Context
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore

object FirebaseConfig {

    fun initialize(context: Context) {

        /*
         * CURRENT FIREBASE PROJECT SETUP THAT WAS WORKING IN TEST WITH PERSONAL FIREBASE
         * Kept for Sprint 2 troubleshooting.
         *
         * FirebaseApp.initializeApp(context)
         *
         * val app = FirebaseApp.getInstance()
         * println("Firebase app loaded: ${app.name}")
         *
         * val auth = FirebaseAuth.getInstance()
         * println("Configured auth instance: ${auth.hashCode()}")
         *
         * val firestore = FirebaseFirestore.getInstance()
         * println("Firestore instance created")
         */



        // BUILDER SETUP BELOW - WAS PREVIOUSLY NOT WORKING

        val options = FirebaseOptions.Builder()
            .setProjectId("demo-al-group11")
            .setApplicationId("1:1234567890:android:agenticlender")
            .setApiKey("demo-api-key")
            .build()

        if (FirebaseApp.getApps(context).isEmpty()) {
            FirebaseApp.initializeApp(context, options)
        }

        val auth = FirebaseAuth.getInstance()

        auth.useEmulator("10.0.2.2", 9099)

        println("Auth emulator configured")

        val firestore = FirebaseFirestore.getInstance()

        firestore.useEmulator("10.0.2.2", 8080)

        println("Firestore emulator configured")
    }
}