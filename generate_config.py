import json
import os
from urllib.parse import urlparse

def create_config_from_json(json_file_path):
    """
    Reads restaurant data from a JSON file and creates a config.php file.

    Args:
        json_file_path (str): The full path to the input JSON file.
    """
    if not os.path.exists(json_file_path):
        print(f"Error: JSON file not found at {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        try:
            final_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {json_file_path}")
            return

    # --- Data Mapping ---
    venue_name = final_data.get("rName", "")
    address = final_data.get("rAddress", "")
    address_parts = address.split(',')
    address_street = address_parts[0].strip() if address_parts else ""
    address_town = final_data.get("rCity", "")
    address_region = final_data.get("rRegion", "")
    address_postal_code = final_data.get("rZip", "")
    website_url = final_data.get("rWebsite", "")
    website_display_url = urlparse(website_url).netloc if website_url else ""
    email = final_data.get("rEmail", "")
    google_map_link = final_data.get("rMaps link", "")
    google_map_id = final_data.get("plac_id", "")
    formatted_phone = final_data.get("rPhone", "")
    # Create the tel: link from the international phone number
    link_phone = final_data.get("rIntPhone", "").replace(" ", "").replace("-", "")
    if not link_phone.startswith("tel:"):
        link_phone = f"tel:{link_phone}"


    # --- Region Mapping ---
    region_map = {
        "auckland": "auckland-region",
        "bay of plenty": "bay-of-plenty-region",
        "canterbury": "canterbury-region",
        "gisborne": "gisborne-region",
        "hawke's bay": "hawkes-bay-region",
        "manawatu-wanganui": "manawatu-wanganui-region",
        "marlborough": "marlborough-region",
        "nelson": "nelson-region",
        "northland": "northland-region",
        "otago": "otago-region",
        "southland": "southland-region",
        "taranaki": "taranaki-region",
        "tasman": "tasman-region",
        "waikato": "waikato-region",
        "wellington": "wellington-region",
        "west coast": "west-coast-region",
    }
    # Determine the correct region variable to uncomment
    php_region_lines = []
    for key, value in region_map.items():
        if key in address_region.lower():
            php_region_lines.append(f'$region = "{value}";')
        else:
            php_region_lines.append(f'//$region = "{value}";')
    php_region_config = "\n".join(php_region_lines)


    # --- PHP File Content ---
    php_config_template = f"""\
<?php
$venueName = '{venue_name}';
$rhSlug = ''; //Restaurant hub slug 1-4-19
$formattedPhone = '{formatted_phone}';//+64 09 928 6079
$linkPhone = '{link_phone}'; //+6499286079 remove zero from front of phone number is using internation code
$address = '{address}'; //2 Graham St, Auckland CBD, Auckland 2104, New Zealand for google maps
//IMPORTANT FOR GOOGLE CALENDER
$addressStreet = "{address_street}"; //eg 1 hight street new 19-6-19
$addressTown ="{address_town}"; //Aucland Queesntown etc new 19-6-19
$addressRegion = "{address_region}"; //Bay of planty , gisborne etc new 19-6-19
$addressPostalCode = "{address_postal_code}"; //new 19-6-19
$websiteURL = '{website_url}';
//END IMPORTANT FOR GOOGLE CALENDER
$websiteDisplayURL = '{website_display_url}';//restauranthub.co.nz
$email = "{email}";
$googleMapLink = "{google_map_link}"; //USE FULL LINK to avoid redirection
$googleMapId ="{google_map_id}";// https://developers.google.com/maps/documentation/places/web-service/place-id
$socialFacebook = "";
$socialInstagram = ""; // no trailing forward slashhttps://www.instagram.com/restauranthub_nz
$socialTripadvisor = ""; // if no TA or fb or Insta then use blank string
$TripAdvisorReview = "";
//Review link for post dining email relpace TA social link Restaurant_Review after the .com/ with UserReviewEdit
$postDiningLinkName = "TripAdvisor review page";
// https://www.restauranthub.co.nz/rh/post-dining-review-collection/?vendor_slug=commons

//$postDiningLink = 'https://www.restauranthub.co.nz/rh/post-dining-review-collection/?vendor_slug='.$rhSlug; //Restaurant hub slug 1-4-19
$postDiningLink = $TripAdvisorReview; // use for no r-hub slug

//lOGO +++++++++++++++++++
//Background change colour or keep white // is a comment and line is ingored
$logoBackground = "#ffffff"; //white default - remove comment
//$logoBackground = "#000000 "; //black - remove comment '//'
//$logoBackground = "#000000 "; //custom here, otherwise comment this line out with '//'
//++++++++++++++++++++++
//NEW 13-02-2019
//Regions - will define the promo image and promo link url - leave only the area specified uncommented
{php_region_config}




/////////////////// regular edit for new restaurant above only

//Review link for post dining email using Google
$postDiningLinkName2 = "Google review page";
// https://www.restauranthub.co.nz/rh/post-dining-review-collection/?vendor_slug=commons
$postDiningLink2 = "https://search.google.com/local/writereview?placeid=$googleMapId"; //Restaurant hub slug 1-4-19 //Restaurant hub slug 1-4-19
$internationalDialCode = "+64"; // new 19-6-19 do not touch

//post dining email add if different from regular email if same leave empty
$postDiningEmail = "";
if (empty($postDiningEmail)) {{$postDiningEmail = $email;}}



//$socialEmail = 'mailto:'.$email; Moved below, set by $email

//EVENTS - note simple event title can be used by placing ?event="Name of Event" or use & if alreaddy using ?venue eg  ../TEMPLATE-confirmation-phone.php?venue=MrMorris&event=Xmas%20Lunch
//EVENT STUFF
$showEventBlock = "none"; // use "none" or "block"
$eventName = ""; //Use this for the event template to show the event name/experience
$eventBoxTitle = "";
$eventBoxTitleDescription = "";
$eventBlurbTitle_1 = "";
$eventBlurbText_1 = "";
$eventBlurbTitle_2 = "";
$eventBlurbText_2 = "";
$eventBlurbTitle_3 = "";
$eventBlurbText_3 = "";
$eventBlurbTitle_4 = "";
$eventBlurbText_4 = "";

//NEW 13-4-23
//$showCustomDetails = "Booking for COVERS guests on DATE at TIME<br />Booking name: FULLNAME<br />";



?>

<?php
	$bannerImageOn = false; // Do we have a banner image - true or false load image in venue dir confirm.jpg
	$contentImage = false; // Do we have a content image - true or false load image in venue dir contentimage.jpg added  030723
	$postdiningImage = false; // set to true if you want a seperate image for post dining - load image in venu dir 'reminder.jpg'
	$adInfo = "";
	$reminderImage = false; // set to true if you want a seperate image for reminder - load image in venu dir 'reminder.jpg'
	// Header title for each template
	$titleRestaurantHide = false; // do you want to show the name of the restaurant in the header (removed for clooney)
	$confirmedMessage = "Reservation Confirmation EVENT";
	$reminderMessage = "Reservation Reminder EVENT";
	//New 25-Feb-2019
	$confirmPrompt = "Please click below to confirm your reservation";
	$cancelMessage = "Your reservation is cancelled";
	//Use this WARNTIME and WARNDATE when they want to AUTO CANCEL
	//$creditCardMessage = "You have until WARNTIME on WARNDATE to register your credit card";
	$creditCardMessage = "Please register your credit card to secure your booking";
	$standbyMessage = "You have been placed on our waiting list";
	$standbyOfferMessage = "Reservation Offer";
	$postDiningMessage = "We hope you enjoyed your experience";
	$customerFooter = false;
	$footerImageExt = "";
	$footerLink = ""; //new 03/08/22
	$promoBannerHide = false; //new 19-6-19 shows or hides promotion banner in footer
	$footerHide = false; //new 19-6-19 shows or hides complete footer, if fasle then make promoBanner false as well
	//TBC more templates ++



	// Configurable text in main section ++++++++++++++++++++++
	$greeting = "Dear";
	$FullName = false; // true for First Name only

	// Blurb after first line before details

	$blurbConfirmation_1 = "Thank you for booking with us.<br><br>Here are all the booking details for your upcoming reservation:";
	$blurbReminder_1 = "We are looking forward to seeing you. <a href='CANCON' title='Confirm your booking' target='_blank'>Click here</a> to to reconfirm your booking.<br><br>Here are all the booking details for your upcoming reservation:";
	$blurbCancel_1 = "Your reservation is cancelled";
	$blurbCCConfirmation_1 = "The confirmation of this booking is subject to the successful registration of payment details, to register please use the link to enter your credit card details via the secure Stripe payment platform.";
	//CC Reminder added 10/02/22
	$blurbCCReminder = "<strong>We have not received your credit card registration or payment for this booking.<br><br>The confirmation of this booking is subject to the successful registration or payment, to register <a href='CANCON' title='Credit card registration link' target='_blank'>click here</a> to confirm reservation and enter your credit card details via the secure Stripe payment platform.</strong>";

	//When a customer wants to automatically cancel - Use this and unticked never purge auto cancel
	//$blurbCCReminder = "<strong>We appear not to have received your credit card registration or payment for this booking. You have until WARNTIME on WARNDATE to register your credit/debit card or your provisional booking will be deleted.</strong><br><br>The confirmation of this booking is subject to the successful registration or payment, to register <a style='color:#000; text-decoration:underline;' href='CANCON' title='Credit card registration link' target='_blank'>click here</a> to confirm reservation and enter your credit card details via the secure Stripe payment platform.";
    $blurbStandby_1 = "Your party has been added to the waitlist.";
	$blurbStandbyOffer_1 = "A table has become available for your requested time. <br />";//"Your party has been added to the waitlist.";


	//New Post Dining text from Ash Google only
	//$blurbPostDining_1='You&#39;ve recently visited us, If you had a wonderful time, we would be incredibly grateful if you could take a few moments to share your experience on our <a href="'.$postDiningLink2.'" title="Google Page Review" target="_blank"><img style="vertical-align: bottom" src="https://emailtemplates.hosting.eveve.co.nz/images/google-page-review.png" width="65" height="22" alt="Google Page Review"/></a> review page. Your glowing reviews not only inspire us to keep raising the bar but also assist fellow diners & travelers in discovering the joys of our establishment.<br><br>Your words have the power to shape perceptions and influence decisions. By sharing your positive encounters, you&#39;re not just endorsing us; you&#39;re contributing to the memories and experiences of future visitors.';

	//New Post Dining text from Ash BOTH TA and Google
	$blurbPostDining_1='You&#39;ve recently visited us, If you had a wonderful time, we would be incredibly grateful if you could take a few moments to share your experience on <a href="'.$postDiningLink.'" title="Tripadvisor" target="_blank"><img style="vertical-align: bottom" src="https://hosting.eveve.co.nz/email_templates/images/tripadvisor-rh.png" width="148" height="22" alt="Tripadvisor"/></a> or our <a href="'.$postDiningLink2.'" title="Google Page Review" target="_blank"><img style="vertical-align: bottom" src="https://emailtemplates.hosting.eveve.co.nz/images/google-page-review.png" width="65" height="22" alt="Google Page Review"/></a> review pages. Your glowing reviews not only inspire us to keep raising the bar but also assist fellow diners & travelers in discovering the joys of our establishment.<br><br>Your words have the power to shape perceptions and influence decisions. By sharing your positive encounters, you&#39;re not just endorsing us; you&#39;re contributing to the memories and experiences of future visitors.';

	//One Off Templates Here
	$oneOffConfirmedMessage = "Your reservation is confirmed";
    $oneOffBlurbConfirmation_1 = "Thank you for booking with us.<br><br>Here are all the booking details for your upcoming reservation:";
    $oneOffBlurbConfirmation_2 = "A 15% surcharge applies to all public holidays.";

	$oneOffReminderMessage = "oneOffReminderMessage";
    $oneOffBlurbReminder = "oneOffBlurbReminder";
    $oneOffBlurbReminder2 = "oneOffBlurbReminder2";
	//End of One off Templates


	$blurbEvent_1 = ""; //.$eventName;

	//Reminder hides
	$dontShowConfirmationNumber = false; //SS 280720
	$dontShowGuestPhone = false; 		//SS 280720

	//Event Show
	$dontShowEventName = true; //use true to show new EVENT placeholder in confirmation template internet

	//Area Show
	$dontshowArea = false;

	$notesInternet = true; // Will only display on internet booking
	$notesPhone = false; // If phone is on phone notes will display on all templates - not recomended

	//If customer is using vacate warning, displays on internet bookings only.
	$vacateWarning = false;

	//Blurb after booking details
	//$blurbConfirmation_2 = "If you have any dietary requirements or allergies, please ensure you let us know as soon as possible as we may be unable accommodate requests unless we know prior to the day.<br><br>We look forward to seeing you then";
	$blurbConfirmation_2 = "We look forward to seeing you and hope you enjoy your experience with us.";
	//$blurbConfirmation_2 = "<strong>Please note:</strong> All New Year’s Eve reservations will be allocated two-hour dining times. A friendly member of our team will advise you when the table is required to be vacated when your booking is made. As per government guidelines all guests of eligible age, will be required to provide proof of being fully vaccinated upon entry.<br><br><strong>Celebrating an Occasion ?</strong><br>If you need a cake for a celebration of any sort, let us know and we can arrange for this to be made in-house. We do need 48 hours to prepare this for you. Please note we don&rsquo;t allow BYO of any food.<br><br>We look forward to seeing you then."; //TEMP_TBD
	$blurbReminder_2 = "";
	$blurbCancel_2 = "Thank you for letting us know, and we hope to see you another time.";
	$blurbCCConfirmation_2 = "Your card will only be charged in the event of a no-show or late cancellation.";
	$blurbCCDepositConfirmation = "We will require payment for this booking in advance, your card will be charged.";
	$blurbCCDepositConfirmation_2 = "";
	$blurbStandby_2 = $blurbStandby_2 = "Please note that this is not a reservation confirmation; You will be advised by email or telephone if a table becomes available. Please reply promptly so that we can offer the table to another guest if you are unable to accept the booking.";
	$blurbStandbyOffer_2 = "We are looking forward to seeing you. <a href='ACCEPT' title='Confirm your booking' target='_blank'>Click here</a> to confirm your booking. <a href='REJECT' title='Reject the booking' target='_blank'>Click here</a> to reject the booking. <br>Please reply promptly so that we can offer the table to another guest if you are unable to accept the booking.";
	//Click here to <a href="ACCEPT">Click to accept the stanby offer</a> or <a href="REJECT">click to Deny the offer</a> (Currently not working 7/2024).
	//$blurbPostDining_2 ='Alternatively, if you would like to contact us directly about your experience you can send an email to <a href="mailto:'.$postDiningEmail.'" target="_blank">'.$postDiningEmail.'</a>.';
	$blurbPostDining_2 ='If, by chance, we&#39;ve fallen short of your expectations and you have constructive feedback to offer, we genuinely invite you to reach out to us directly at <a href="mailto:'.$postDiningEmail.'" target="_blank">'.$postDiningEmail.'</a>.<br><br>Thank you for being a part of our journey, and we look forward to welcoming you back soon!';
	//Info section
	$infoTitleMain = "Helpful tips and information"; //Title of Info section

	//CHANGE BOOKING - if using telephone, use true, if using email use false - make sure email is completed above
	$hideTheWholeBanner = false; //SS 280720
	$dontAllowChange = false; // No Cancel box or Change box at all NEW 09-09-19
	$callToChange = true; // How are the customers going to change booking default is phone only one of these should be true
	$callAndEmail = false;
	$emailToChange = false;
	$changeBookingIcon = "https://emailtemplates.hosting.eveve.co.nz/images/phone-solid.png";
	$infoChangeBookingTitle = 'Need to make a change to your booking?';
	if ($callAndEmail) {{
		$emailLink = 'mailto:'.$email;
		$infoChangeBooking = 'If you need to make a change to this booking:<br>Please call <a href="'.$linkPhone.'">'.$formattedPhone.'</a> or email us on <a href="'.$emailLink.'">'.$email.'</a>.';
		$changeBookingIcon = "https://emailtemplates.hosting.eveve.co.nz/images/phone-email.png";
	}}
	if ($callToChange) {{
		$infoChangeBooking = 'If you need to make a change to this booking, please call<br><a href="'.$linkPhone.'">'.$formattedPhone.'</a>';
		$changeBookingIcon = "https://emailtemplates.hosting.eveve.co.nz/images/phone-solid.png";
	}}
	if ($emailToChange) {{
		$emailLink = 'mailto:'.$email;
		$infoChangeBooking = 'If you need to make a change to this booking, please send us an email at <a href="'.$emailLink.'">'.$email.'</a>';
		$changeBookingIcon = "https://emailtemplates.hosting.eveve.co.nz/images/email-change.png";
	}}
	$socialEmail = 'mailto:'.$email;

	//Cancel booking is it allowed - default is true (TBC for top section)
	$cancelAllowed = true;
	$cancelInfoTitle = 'Need to cancel your booking?';
	$cancelInfo = "<a href='CANCON' title='Cancel your booking' target='_blank'>Click here if you need to cancel your booking.</a>";

	// Additional info
	$infoTitle_1 = '';
	$info_1 = '';
	$infoTitle_2 = '';
	$info_2 = '';
	$infoTitle_3 = '';
	$info_3 = '';
	$infoTitle_4 = '';
	$info_4 = '';
	$infoTitle_5 = '';
	$info_5 = '';

	//Booking policy
	$bookingPolicy = true;
	$bookingPolicy_url = '';
	$bookingPolicy_title = 'Booking Policy';
	$bookingPolicy_1 = 'We really appreciate you arriving on time, as we will only be able to hold tables for 15 minutes from the time you have booked. Please contact us directly should you be running late, or if have any last-minute changes to your numbers. We will do our best to accommodate your request.';

	//$bookingPolicy_2 = 'Cancellations within XX hours or changes to the group size by X or more without notice may incur a fee of $XX per person (or the menu price for special events). Any cancellation fees will be deducted from the registered card on file and the person responsible for the booking will be notified by email.';

	$bookingPolicy_3 = '';

	$bookingPolicy_4 = '';

	$bookingPolicy_5 = '';

	$bookingPolicy_6 = '';

	$bookingPolicy_7 = '';

	$bookingPolicy_8 = '';

	//Maps DO not

	$addressWithSeperator = preg_replace('/\\s+/', '+', $address);
	$googleNoSpaceVenueName = preg_replace('/\\s+/', '+', $venueName);
	//$mapImage = '<a href="'.$googleMapLink.'" target="_blank"><img border="0" width="250" src="https://maps.googleapis.com/maps/api/staticmap?center='.$googleNoSpaceVenueName.'+'.$addressWithSeperator. '&zoom=16&scale=2&size=250x158&maptype=roadmap&key=AIzaSyCrCnCW5Gz4Af2oVlKjrviroE0ZymGtCDU&format=png&visual_refresh=true&markers=size:mid%7Ccolor:0xff8000%7Clabel:%7C'.$venueName.'+'.$addressWithSeperator.'&style=feature:poi|element:labels|visibility:off" alt="Google Map of '.$venueName.'+'.$addressWithSeperator.'" ></a>';
	//print($mapImage); //test and link

	$getTheMap = '<img border="0" width="250" src="https://maps.googleapis.com/maps/api/staticmap?center='.$googleNoSpaceVenueName.'+'.$addressWithSeperator. '&zoom=16&scale=2&size=250x158&maptype=roadmap&key=AIzaSyBh1ldp_HKC19Q3NrGnkgLdF_1sabuAehI&format=png&visual_refresh=true&markers=size:mid%7Ccolor:0xff8000%7Clabel:%7C'.$venueName.'+'.$addressWithSeperator.'&style=feature:poi|element:labels|visibility:off" alt="Google Map of '.$venueName.'+'.$addressWithSeperator.'" >';
	//print($mapImage); //test and link

	//USE A REAL MAP to help spam score
	$mapImage = '<a href="'.$googleMapLink.'" target="_blank"><img border="0" style="border:1px solid #ccc" width="250" src="https://emailtemplates.hosting.eveve.co.nz/venue/'.$venueDir.'/staticmap.png" alt="Google Map of '.$venueName.'+'.$addressWithSeperator.'" ></a>';

//print($mapImage); //test and link

	//added 11 feb19;
	$signatureShow = true;
	$signature = "Warmest Regards,<br><br>".$venueName;
	if(!$signature) $signature=$venueName;

	$customSign = ""; //used on post dining emails only to personalize

	//SMTP Setting if required - default to false to use normal server 99% will use default
	$smtp = false;
	$smtpServer = "mail.reservations.eveve.co.nz";
	$smtpUserName = "";
	$smtpPassword = "";
	$smtpPort = "25";
	$smtpSecure = "false";


//Gift Card Start
$blurbGiftCard_1 = "Book a table online at <a href='". $websiteURL."' class='link' style='color:#64a6d7; text-decoration:none' target='_blank'>
<span class='link' style='color:#64a6d7; text-decoration:none'>". $websiteDisplayURL."</span></a><br><br>Please bring this email along with you to redeem your gift card.";

//Gift Card End

?>
"""

    # --- File Saving ---
    # The output file will be saved in the same directory as the input JSON file.
    output_dir = os.path.dirname(json_file_path)
    output_filename = os.path.join(output_dir, "config.php")

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(php_config_template)

    print(f"Successfully created config.php at: {output_filename}")

if __name__ == '__main__':
    # This script is designed to be called from the main script,
    # but can be run standalone for testing if a JSON file path is provided.
    import sys
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        create_config_from_json(json_path)
    else:
        print("Usage: python generate_config.py <path_to_restaurant.json>")
