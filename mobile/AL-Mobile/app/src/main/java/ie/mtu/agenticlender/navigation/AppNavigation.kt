package ie.mtu.agenticlender.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import ie.mtu.agenticlender.screens.BorrowingEstimateScreen
import ie.mtu.agenticlender.screens.LoanApplicationScreen
import ie.mtu.agenticlender.screens.LoginScreen
import ie.mtu.agenticlender.screens.MyApplicationScreen
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
                },
                // AL-8 / AL-7: a returning borrower can go straight to their application
                onViewApplication = {
                    navController.navigate("myApplication")
                },
                // AL-3 US-111: borrowing estimate
                onEstimate = {
                    navController.navigate("borrowingEstimate")
                }
            )
        }

        // AL-3 US-111 Enter income, debts, deposit and term for borrowing estimate
        composable("borrowingEstimate") {

            BorrowingEstimateScreen(
                onBack = { navController.popBackStack() }
            )
        }

        composable("loanApplication") {

            LoanApplicationScreen(
                valuationDraft = valuationDraft,
                // AL-8 / AL-7: after submitting, follow the application's progress
                onViewApplication = {
                    navController.navigate("myApplication")
                }
            )
        }

        // AL-8 US-132 lifecycle timeline + AL-7 US-131 LTV and DTI
        composable("myApplication") {

            MyApplicationScreen(
                // popBackStack() goes back one screen, like the phone's Back button
                onBack = { navController.popBackStack() }
            )
        }
    }
}