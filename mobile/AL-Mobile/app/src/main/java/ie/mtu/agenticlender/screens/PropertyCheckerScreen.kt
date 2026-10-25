package ie.mtu.agenticlender.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

import com.google.firebase.auth.FirebaseAuth
import ie.mtu.agenticlender.api.RetrofitClient
import ie.mtu.agenticlender.api.ValuationRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PropertyCheckerScreen(
    onContinue: () -> Unit
) {

    var county by remember { mutableStateOf("") }
    var floorArea by remember { mutableStateOf("") }
    var bedrooms by remember { mutableStateOf("") }
    var propertyType by remember { mutableStateOf("") }
    var ber by remember { mutableStateOf("") }

    var estimate by remember { mutableStateOf("") }
    var lowEstimate by remember { mutableStateOf("") }
    var highEstimate by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }

    var countyExpanded by remember { mutableStateOf(false) }
    var propertyExpanded by remember { mutableStateOf(false) }
    var berExpanded by remember { mutableStateOf(false) }

    var modelVersion by remember { mutableStateOf("") }
    var valuationId by remember { mutableStateOf("") }

    val scope = rememberCoroutineScope()

    val counties = listOf(
        "Carlow",
        "Cavan",
        "Clare",
        "Cork",
        "Donegal",
        "Dublin",
        "Galway",
        "Kerry",
        "Kildare",
        "Kilkenny",
        "Laois",
        "Leitrim",
        "Limerick",
        "Longford",
        "Louth",
        "Mayo",
        "Meath",
        "Monaghan",
        "Offaly",
        "Roscommon",
        "Sligo",
        "Tipperary",
        "Waterford",
        "Westmeath",
        "Wexford",
        "Wicklow"
    )

    val propertyTypes = listOf(
        "apartment",
        "terraced",
        "semi_detached",
        "detached",
        "bungalow"
    )

    val berRatings = listOf(
        "A1", "A2", "A3",
        "B1", "B2", "B3",
        "C1", "C2", "C3",
        "D1", "D2",
        "E1", "E2",
        "F", "G"
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {

        Text(
            text = "Property Checker",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(modifier = Modifier.height(16.dp))

        // COUNTY DROPDOWN

        ExposedDropdownMenuBox(
            expanded = countyExpanded,
            onExpandedChange = { countyExpanded = !countyExpanded }
        ) {
            OutlinedTextField(
                value = county,
                onValueChange = {},
                readOnly = true,
                label = { Text("County") },
                modifier = Modifier
                    .fillMaxWidth()
                    .menuAnchor()
            )

            ExposedDropdownMenu(
                expanded = countyExpanded,
                onDismissRequest = { countyExpanded = false }
            ) {
                counties.forEach { countyItem ->
                    DropdownMenuItem(
                        text = { Text(countyItem) },
                        onClick = {
                            county = countyItem
                            countyExpanded = false
                        }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedTextField(
            value = floorArea,
            onValueChange = { floorArea = it },
            label = { Text("Floor Area (m²)") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedTextField(
            value = bedrooms,
            onValueChange = { bedrooms = it },
            label = { Text("Bedrooms") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(8.dp))

        // PROPERTY TYPE DROPDOWN

        ExposedDropdownMenuBox(
            expanded = propertyExpanded,
            onExpandedChange = { propertyExpanded = !propertyExpanded }
        ) {
            OutlinedTextField(
                value = propertyType,
                onValueChange = {},
                readOnly = true,
                label = { Text("Property Type") },
                modifier = Modifier
                    .fillMaxWidth()
                    .menuAnchor()
            )

            ExposedDropdownMenu(
                expanded = propertyExpanded,
                onDismissRequest = { propertyExpanded = false }
            ) {
                propertyTypes.forEach { type ->
                    DropdownMenuItem(
                        text = { Text(type) },
                        onClick = {
                            propertyType = type
                            propertyExpanded = false
                        }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // BER DROPDOWN

        ExposedDropdownMenuBox(
            expanded = berExpanded,
            onExpandedChange = { berExpanded = !berExpanded }
        ) {
            OutlinedTextField(
                value = ber,
                onValueChange = {},
                readOnly = true,
                label = { Text("BER Rating") },
                modifier = Modifier
                    .fillMaxWidth()
                    .menuAnchor()
            )

            ExposedDropdownMenu(
                expanded = berExpanded,
                onDismissRequest = { berExpanded = false }
            ) {
                berRatings.forEach { rating ->
                    DropdownMenuItem(
                        text = { Text(rating) },
                        onClick = {
                            ber = rating
                            berExpanded = false
                        }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        Button(
            onClick = {
                errorMessage = "BUTTON CLICKED"
                println("BUTTON CLICKED")

                estimate = ""
                lowEstimate = ""
                highEstimate = ""
                modelVersion = ""
                valuationId = ""

                if (county.isBlank()) {
                    errorMessage = "County is required"
                }
                else if (
                    floorArea.toIntOrNull() == null ||
                    floorArea.toInt() <= 0
                ) {
                    errorMessage =
                        "Floor area must be greater than 0"
                }
                else if (
                    bedrooms.toIntOrNull() == null ||
                    bedrooms.toInt() <= 0
                ) {
                    errorMessage =
                        "Bedrooms must be greater than 0"
                }
                else if (propertyType.isBlank()) {
                    errorMessage = "Property type is required"
                }
                else if (ber.isBlank()) {
                    errorMessage = "BER rating is required"
                }


                else {

                    loading = true
                    println("VALIDATION PASSED")

                    scope.launch(Dispatchers.IO) {

                        try {

                            /*
                            val tokenResult =
                                FirebaseAuth.getInstance()
                                    .currentUser
                                    ?.getIdToken(false)

                            tokenResult?.addOnSuccessListener { token ->

                                scope.launch {

                                    try {
                                        println("CALLING /valuations")
                                        val response =

                                            RetrofitClient.api.createValuation(
                                                "Bearer ${token.token}",
                                                ValuationRequest(
                                                    county = county,
                                                    floorAreaM2 = floorArea.toDouble(),
                                                    bedrooms = bedrooms.toInt(),
                                                    propertyType = propertyType,
                                                    ber = ber
                                                )
                                            )
                                        println("VALUATION RESPONSE CODE = ${response.code()}")

                                        if (response.isSuccessful) {

                                            response.body()?.let {

                                                estimate = "€${it.estimate}"
                                                lowEstimate = "€${it.low}"
                                                highEstimate = "€${it.high}"
                                                modelVersion = it.modelVersion
                                                valuationId = it.valuationId
                                                println("VALUATION SUCCESS")
                                                println(it)
                                            }

                                        } else {
                                            errorMessage =
                                                "API Error ${response.code()}"
                                        }

                                    } catch (e: Exception) {

                                        errorMessage =
                                            e.message ?: "Unknown error"
                                    }

                                    loading = false
                                }
                            }
                            */

                            println("Current user = ${FirebaseAuth.getInstance().currentUser}")
                            println("Email = ${FirebaseAuth.getInstance().currentUser?.email}")

                            println("CALLING /valuations")

                            println("Current user: ${FirebaseAuth.getInstance().currentUser?.email}")
                            println("Request county: $county")
                            println("Request area: $floorArea")

                            println("THREAD = ${Thread.currentThread().name}")

                            println("Current user = ${FirebaseAuth.getInstance().currentUser?.email}")
                            println("Thread = ${Thread.currentThread().name}")

                            println("CALLING /health via Retrofit...")
                            try {
                                val healthResponse = RetrofitClient.api.health()
                                println("HEALTH RESPONSE CODE = ${healthResponse.code()}")
                                println("HEALTH RESPONSE BODY = ${healthResponse.body()?.string()}")
                            } catch (e: Exception) {
                                println("HEALTH EXCEPTION = ${e.message}")
                            }

                            val response =
                                RetrofitClient.api.createValuation(
                                    "",
                                    ValuationRequest(
                                        county = county,
                                        floorAreaM2 = floorArea.toDouble(),
                                        bedrooms = bedrooms.toInt(),
                                        propertyType = propertyType,
                                        ber = ber
                                    )
                                )

                            println("VALUATION RESPONSE CODE = ${response.code()}")

                            if (response.isSuccessful) {

                                response.body()?.let {

                                    println("VALUATION SUCCESS")
                                    println(it)

                                    estimate = "€${it.estimate}"
                                    lowEstimate = "€${it.low}"
                                    highEstimate = "€${it.high}"
                                    modelVersion = it.modelVersion
                                    valuationId = it.valuationId
                                }

                            } else {

                                errorMessage =
                                    "API Error ${response.code()}"
                            }

                        } catch (e: Exception) {

                            println("VALUATION EXCEPTION")
                            println(e.toString())

                            e.printStackTrace()

                            errorMessage = e.toString()

                            loading = false
                        }
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Get Fair-Value Estimate")
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (loading) {

            CircularProgressIndicator()

            Spacer(
                modifier = Modifier.height(12.dp)
            )
        }

        if (errorMessage.isNotEmpty()) {
            Text(
                text = errorMessage,
                color = MaterialTheme.colorScheme.error
            )
        }

        if (estimate.isNotEmpty()) {

            Spacer(modifier = Modifier.height(12.dp))

            Card(
                modifier = Modifier.fillMaxWidth()
            ) {

                Column(
                    modifier = Modifier.padding(16.dp)
                ) {

                    Text(
                        text = "Estimated Value: $estimate",
                        style = MaterialTheme.typography.titleMedium
                    )

                    Spacer(
                        modifier = Modifier.height(4.dp)
                    )

                    Text(
                        text = "Low Estimate: $lowEstimate"
                    )

                    Text(
                        text = "High Estimate: $highEstimate"
                    )

                    Text(
                        text = "Model Version: $modelVersion"
                    )

                    Text(
                        text = "Valuation ID: $valuationId"
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Continue to Loan Application")
        }
    }
}