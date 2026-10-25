package ie.mtu.agenticlender.firebase

import android.content.Context
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore

object FirebaseConfig {

    fun initialize(context: Context) {

        if (FirebaseApp.getApps(context).isEmpty()) {
            val options = FirebaseOptions.Builder()
                .setProjectId("demo-al-group11")
                .setApplicationId("1:1234567890:android:agenticlender")
                .setApiKey("demo-api-key")
                .build()

            FirebaseApp.initializeApp(context, options)
        }

        val auth = FirebaseAuth.getInstance()
        try {
            auth.useEmulator("192.168.0.50", 9099)
            println("Firebase Auth emulator configured on 192.168.0.50:9099")
        } catch (e: Exception) {
            println("Firebase Auth emulator error: ${e.message}")
        }

        val firestore = FirebaseFirestore.getInstance()
        try {
            firestore.useEmulator("192.168.0.50", 8080)
            println("Firestore emulator configured on 192.168.0.50:8080")
        } catch (e: Exception) {
            println("Firestore emulator error: ${e.message}")
        }
    }
}
