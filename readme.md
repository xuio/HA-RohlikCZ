# Rohlik.cz Integration for Home Assistant

This custom component provides integration with [Rohlik.cz](https://www.rohlik.cz), the popular Czech food delivery service. It allows you to monitor your Rohlik.cz account information, shopping cart, delivery status, and premium membership details directly in Home Assistant.

> [!CAUTION] 
> This integration is made by reverse engineering API that is used by the rohlik.cz website. Use this integration at your own risk.

## Installation

### Using [HACS](https://hacs.xyz/)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dvejsada&repository=HA-RohlikCZ&category=Integration)

### Manual Installation

To install this integration manually, download the `rohlikcz` folder into your `config/custom_components` directory.

## Configuration

### Using UI

From the Home Assistant front page go to **Configuration** and then select **Integrations** from the list.

Use the "plus" button in the bottom right to add a new integration called **Rohlik.cz**.

Fill in:
 
- Email (your Rohlik.cz account email)
- Password (your Rohlik.cz account password)

The integration will connect to your Rohlik.cz account and set up the entities.

## Features

The integration provides the following entities:

### Binary Sensors

- **Premium Membership** - Shows if your premium membership is active with additional premium details as attributes
- **Reusable Bags** - Indicates if you're using reusable bags with information about the number of bags in your account
- **Next Order** - Shows if you have a scheduled order with order details as attributes
- **Timeslot Reservation** - Shows if you have reserved a delivery timeslot
- **Parents Club** - Indicates if you're a member of the Parents Club

### Sensors

- **First Available Delivery** - Shows the earliest available delivery time with location details
- **Account ID** - Your Rohlik.cz account ID
- **Email** - Your Rohlik.cz email address
- **Phone** - Your registered phone number
- **Remaining Orders Without Limit** - Number of premium orders without minimum price limit available
- **Remaining Free Express Deliveries** - Number of free express deliveries available
- **Credit Balance** - Your account credit balance
- **Reusable Bags** - Number of bags in your account
- **Premium Days Remaining** - Days left in your premium membership (only appears for premium users)
- **Cart Total** - Current shopping cart total
- **Last Updated** - Timestamp of the last data update from Rohlik.cz

## Data Updates

The integration updates data from Rohlik.cz periodically every 10 minutes by default. The data includes your account details, premium status, delivery options, shopping cart, and more.

## Development

This integration is based on unofficial API access to Rohlik.cz. While efforts are made to keep it working, changes to the Rohlik.cz platform may affect functionality.
