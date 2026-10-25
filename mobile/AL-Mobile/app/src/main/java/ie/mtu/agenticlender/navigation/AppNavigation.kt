package ie.mtu.agenticlender.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import ie.mtu.agenticlender.screens.LoanApplicationScreen
import ie.mtu.agenticlender.screens.LoginScreen
import ie.mtu.agenticlender.screens.PropertyCheckerScreen
import ie.mtu.agenticlender.screens.RegisterScreen

@Composable
fun AppNavigation() {

    val navController = rememberNavController()

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
                onContinue = {
                    navController.navigate("loanApplication")
                }
            )
        }

        composable("loanApplication") {

            LoanApplicationScreen()
        }
    }
}