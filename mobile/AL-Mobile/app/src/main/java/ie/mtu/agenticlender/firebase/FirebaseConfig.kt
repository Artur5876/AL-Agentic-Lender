package ie.mtu.agenticlender.firebase

import android.content.Context
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore

object FirebaseConfig {

    fun initialize(context: Context) {

        if (FirebaseApp.getApps(context).isEmpty()) {
            FirebaseApp.initializeApp(context)
        }

        val auth = FirebaseAuth.getInstance()

        println("Firebase Auth configured")

        val firestore = FirebaseFirestore.getInstance()

        println("Firestore configured")
    }

        /*
         * BUILDER SETUP - DID NOT WORK
         *
         * val options = FirebaseOptions.Builder()
         *     .setProjectId("demo-al-group11")
         *     .setApplicationId("1:1234567890:android:agenticlender")
         *     .setApiKey("demo-api-key")
         *     .build()
         *
         * if (FirebaseApp.getApps(context).isEmpty()) {
         *     FirebaseApp.initializeApp(context, options)
         * }
         */
}
