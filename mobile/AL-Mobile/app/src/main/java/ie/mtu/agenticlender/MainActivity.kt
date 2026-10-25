package ie.mtu.agenticlender

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import ie.mtu.agenticlender.firebase.FirebaseConfig
import ie.mtu.agenticlender.navigation.AppNavigation
import ie.mtu.agenticlender.ui.theme.ALMobileTheme
import com.google.firebase.auth.FirebaseAuth

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        FirebaseConfig.initialize(this)
        println(
            "Current User: ${
                FirebaseAuth.getInstance().currentUser?.email
            }"
        )

        enableEdgeToEdge()

        setContent {
            ALMobileTheme {
                AppNavigation()
            }
        }
    }
}