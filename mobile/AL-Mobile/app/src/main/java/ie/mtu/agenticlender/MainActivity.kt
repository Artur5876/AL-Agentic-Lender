package ie.mtu.agenticlender

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import ie.mtu.agenticlender.screens.LoginScreen
import ie.mtu.agenticlender.ui.theme.ALMobileTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        enableEdgeToEdge()

        setContent {
            ALMobileTheme {

                LoginScreen()

                // Later:
                // RegisterScreen()
                // PropertyCheckerScreen()
                // LoanApplicationScreen()

            }
        }
    }
}