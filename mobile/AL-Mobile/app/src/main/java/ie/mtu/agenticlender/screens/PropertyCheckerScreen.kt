package ie.mtu.agenticlender.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PropertyCheckerScreen() {

    var county by remember { mutableStateOf("") }
    var floorArea by remember { mutableStateOf("") }
    var bedrooms by remember { mutableStateOf("") }
    var propertyType by remember { mutableStateOf("") }
    var ber by remember { mutableStateOf("") }
    var askingPrice by remember { mutableStateOf("") }

    var estimate by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf("") }

    var countyExpanded by remember { mutableStateOf(false) }
    var propertyExpanded by remember { mutableStateOf(false) }
    var berExpanded by remember { mutableStateOf(false) }

    val counties = listOf(
        "Antrim",
        "Armagh",
        "Carlow",
        "Cavan",
        "Clare",
        "Cork",
        "Derry",
        "Donegal",
        "Down",
        "Dublin",
        "Fermanagh",
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
        "Tyrone",
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

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedTextField(
            value = askingPrice,
            onValueChange = { askingPrice = it },
            label = { Text("Asking Price (€)") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(20.dp))

        Button(
            onClick = {

                errorMessage = ""
                estimate = ""

                if (county.isBlank()) {
                    errorMessage = "County is required"
                }
                else if (floorArea.isBlank()) {
                    errorMessage = "Floor area is required"
                }
                else if (bedrooms.isBlank()) {
                    errorMessage = "Bedrooms are required"
                }
                else if (propertyType.isBlank()) {
                    errorMessage = "Property type is required"
                }
                else if (ber.isBlank()) {
                    errorMessage = "BER rating is required"
                }
                else if (askingPrice.isBlank()) {
                    errorMessage = "Asking price is required"
                }
                else {

                    /*
                     * TODO US-121
                     *
                     * Replace this stub with:
                     *
                     * POST http://10.0.2.2:8000/valuations
                     *
                     * Request:
                     * county
                     * floorAreaM2
                     * bedrooms
                     * propertyType
                     * ber
                     *
                     * Response:
                     * valuationId
                     * estimate
                     * low
                     * high
                     *
                     * Display returned estimate here.
                     */

                    estimate = "€$askingPrice"
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Get Fair-Value Estimate")
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (errorMessage.isNotEmpty()) {
            Text(
                text = errorMessage,
                color = MaterialTheme.colorScheme.error
            )
        }

        if (estimate.isNotEmpty()) {

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "Estimated Value: $estimate",
                style = MaterialTheme.typography.titleMedium
            )
        }
    }
}