package ie.mtu.agenticlender.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import ie.mtu.agenticlender.screens.LoanApplicationScreen
import ie.mtu.agenticlender.screens.LoginScreen
import ie.mtu.agenticlender.screens.PropertyCheckerScreen
import ie.mtu.agenticlender.screens.RegisterScreen
import ie.mtu.agenticlender.api.ValuationDraft

@Composable
fun AppNavigation() {

    val navController = rememberNavController()
    var valuationDraft by remember { mutableStateOf<ValuationDraft?>(null) }

    NavHost(
        navController = navController,
        startDestination = "login"
    ) {

        composable("login") {

            LoginScreen(
                onLoginSuccess = {
                    navController.navigate("propertyChecker") {
                        popUpTo("login") { inclusive = true }
                    }
                },
                onRegisterClick = {
                    navController.navigate("register")
                }
            )
        }

        composable("register") {

            RegisterScreen(
                onRegisterSuccess = {
                    navController.navigate("propertyChecker") {
                        popUpTo("register") { inclusive = true }
                    }
                },
                onBackToLogin = {
                    navController.popBackStack()
                }
            )
        }

        composable("propertyChecker") {

            PropertyCheckerScreen(
                onContinue = { draft ->
                    valuationDraft = draft
                    navController.navigate("loanApplication")
                }
            )
        }

        composable("loanApplication") {

            LoanApplicationScreen(valuationDraft = valuationDraft)
        }
    }
}