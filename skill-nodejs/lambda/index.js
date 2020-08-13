/*
 * Copyright 2019 Amazon.com, Inc. or its affiliates.  All Rights Reserved.
 *
 * You may not use this file except in compliance with the terms and conditions 
 * set forth in the accompanying LICENSE.TXT file.
 *
 * THESE MATERIALS ARE PROVIDED ON AN "AS IS" BASIS. AMAZON SPECIFICALLY DISCLAIMS, WITH 
 * RESPECT TO THESE MATERIALS, ALL WARRANTIES, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING 
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
*/

// This skill uses source code provided in https://www.hackster.io/alexagadgets/ 
const Alexa = require('ask-sdk-core');
const Util = require('./util');
const Common = require('./common');

// Import language strings containing all skill voice messages
// e.g. handlerInput.t('WELCOME_MSG')
const i18n = require('i18next');
// const languageStrings = require('./localisation');

// The audio tag to include background music
const DOG_SMALL_BARK_AUDIO = '<audio src="soundbank://soundlibrary/animals/amzn_sfx_dog_small_bark_2x_01"></audio>';

const COMMANDS_LIST = ['COMMAND_REMIND_MSG', 'HELP_COMMAND_MSG'];
// List of welcome greetings
const DOG_COMMAND_LIST = ['COMMAND_SIT_MSG','COMMAND_STAY_MSG','COMMAND_COME_MSG', 'COMMAND_HEEL_MSG', 'COMMAND_SPEAK_MSG'];

// The namespace of the custom directive to be sent by this skill
const NAMESPACE = 'Custom.Mindstorms.Gadget';

// The name of the custom directive to be sent this skill
const NAME_CONTROL = 'control';

const LaunchRequestHandler = {
    canHandle(handlerInput) {
        const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
        const launchCount = sessionAttributes['launchCount'] || 0;

        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'LaunchRequest';
    },
    handle: async function(handlerInput) {

        const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();

        const request = handlerInput.requestEnvelope;
        const { apiEndpoint, apiAccessToken } = request.context.System;
        const apiResponse = await Util.getConnectedEndpoints(apiEndpoint, apiAccessToken);
        console.log("apiResponse: " + apiResponse);
        
        // let speakOutput = handlerInput.t('NO_EV3_FOUND_MSG');
        if ((apiResponse.endpoints || []).length === 0) {
            return handlerInput.responseBuilder
            .speak(`I couldn't find an EV3 Brick connected to this Echo device. Please check to make sure your EV3 Brick is connected, and try again.`)
            .getResponse();
        }

        // Store the gadget endpointId to be used in this skill session
        const endpointId = apiResponse.endpoints[0].endpointId || [];
        Util.putSessionAttribute(handlerInput, 'endpointId', endpointId);

        // Set skill duration to 5 minutes (ten 30-seconds interval)
        //Util.putSessionAttribute(handlerInput, 'duration', 10);

        // Set the token to track the event handler
        const token = handlerInput.requestEnvelope.request.requestId;
        Util.putSessionAttribute(handlerInput, 'token', token);

        
        const launchCount = sessionAttributes['launchCount'];

        let speechOutput = '';
        if (launchCount === 1) {
            speechOutput = handlerInput.t('WELCOME_GREETING_MSG');
        } else {
            speechOutput = handlerInput.t('WELCOME_GREETING_MSG') + handlerInput.t(randomChoice(DOG_COMMAND_LIST));
        }
        // starting point
        return handlerInput.responseBuilder
            .speak(DOG_SMALL_BARK_AUDIO + speechOutput)
            .withShouldEndSession(false)
            .addDirective(Util.buildStartEventHandler(token,60000, {}))
            .getResponse();
    }
};


// Construct and send a custom directive to the connected gadget with data from
// the SetCommandIntent.
const SetCommandIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'SetCommandIntent';
    },
    handle: function (handlerInput) {

        let command = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Command');
        if (!command) {
            return handlerInput.responseBuilder
                .speak(handlerInput.t('REPEAT_COMMANDS_MSG'))
                .withShouldEndSession(false)
                .getResponse();
        }

        const attributesManager = handlerInput.attributesManager;
        let endpointId = attributesManager.getSessionAttributes().endpointId || [];

        // Construct the directive with the payload containing the command
        let directive = Util.build(endpointId, NAMESPACE, NAME_CONTROL,
            {
                type: 'command',
                command: command
            });
            

        let speechOutput = handlerInput.t('COMMAND_TEXT') + `${command}` + handlerInput.t('ACTIVATED_TEXT');

        if( command === 'speak' || command === 'laut') {
            speechOutput = DOG_SMALL_BARK_AUDIO;
        }
        return handlerInput.responseBuilder
            .speak(speechOutput)
            .addDirective(directive)
            .getResponse();
    }
};

const EventsReceivedRequestHandler = {
    // Checks for a valid token and endpoint.
    canHandle(handlerInput) {
        let { request } = handlerInput.requestEnvelope;
        if (request.type !== 'CustomInterfaceController.EventsReceived') return false;

        const attributesManager = handlerInput.attributesManager;
        let sessionAttributes = attributesManager.getSessionAttributes();
        let customEvent = request.events[0];

        // Validate event token
        if (sessionAttributes.token !== request.token) {
            console.log("Event token doesn't match. Ignoring this event");
            return false;
        }

        // Validate endpoint
        let requestEndpoint = customEvent.endpoint.endpointId;
        if (requestEndpoint !== sessionAttributes.endpointId) {
            console.log("Event endpoint id doesn't match. Ignoring this event");
            return false;
        }
        return true;
    },
    handle(handlerInput) {

        console.log("== Received Custom Event ==");
        let customEvent = handlerInput.requestEnvelope.request.events[0];
        let payload = customEvent.payload;
        console.log(JSON.stringify(payload));
        let name = customEvent.header.name;

        let speechOutput;
        if (name === 'bark') {
            return handlerInput.responseBuilder
                .speak(DOG_SMALL_BARK_AUDIO)
                .withShouldEndSession(false)
                .getResponse();
        } else {
            speechOutput = handlerInput.t('UNKNOWN_EVENT_MSG');
        }
        return handlerInput.responseBuilder
            .speak(handlerInput.t(speechOutput))
            .getResponse();
    }
};
const ExpiredRequestHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'CustomInterfaceController.Expired'
    },
    handle(handlerInput) {

        // Set the token to track the event handler
        const token = handlerInput.requestEnvelope.request.requestId;
        Util.putSessionAttribute(handlerInput, 'token', token);

        const attributesManager = handlerInput.attributesManager;
        let duration = attributesManager.getSessionAttributes().duration || 0;
        if (duration > 0) {
            Util.putSessionAttribute(handlerInput, 'duration', --duration);

            const speechOutput = handlerInput.t(randomChoice(COMMANDS_LIST));
            // Extends skill session
            return handlerInput.responseBuilder
                .addDirective(Util.buildStartEventHandler(token, 60000, {}))
                .speak(speechOutput)
                .getResponse();
        }
        else {
            // End skill session
            return handlerInput.responseBuilder
                .speak(handlerInput.t('GOODBYE_MSG') + DOG_SMALL_BARK_AUDIO)
                .withShouldEndSession(true)
                .getResponse();
        }
    }
};

// 2. Helper Functions ============================================================================

function randomChoice(array) {
  // the argument is an array [] of words or phrases
  const i = Math.floor(Math.random() * array.length);
  return (array[i]);
}

// const LocalisationRequestInterceptor = {
//     process(handlerInput) {
//         i18n.init({
//             lng: handlerInput.requestEnvelope.request.locale,
//             resources: languageStrings
//         }).then((t) => {
//             handlerInput.t = (...args) => t(...args);
//         });
//     }
// };

// The SkillBuilder acts as the entry point for your skill, routing all request and response
// payloads to the handlers above. Make sure any new handlers or interceptors you've
// defined are included below. The order matters - they're processed top to bottom.
exports.handler = Alexa.SkillBuilders.custom()
    .addRequestHandlers(
        LaunchRequestHandler,
        SetCommandIntentHandler,
        EventsReceivedRequestHandler,
        ExpiredRequestHandler,
        Common.HelpIntentHandler,
        Common.CancelAndStopIntentHandler,
        Common.SessionEndedRequestHandler,
        Common.IntentReflectorHandler, // make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
    )
    .addRequestInterceptors(
        // LocalisationRequestInterceptor,
        Common.RequestInterceptor,
    )
    .addErrorHandlers(
        Common.ErrorHandler,
    )
    .lambda();
