// src/lib/analytics/posthog.js
import posthog from 'posthog-js';

let isInitialized = false;

export function initPostHog() {
  if (isInitialized) return;
  const enabled = process.env.REACT_APP_POSTHOG_ENABLED === 'true';
  const key = process.env.REACT_APP_POSTHOG_KEY;
  if (!enabled || !key) return;
  const host = process.env.REACT_APP_POSTHOG_HOST || 'https://us.i.posthog.com';
  posthog.init(key, {
    api_host: host,
  });
  isInitialized = true;
}

export function captureEvent(event, properties) {
  if (isInitialized) {
    posthog.capture(event, properties);
  }
}

export function identifyUser(id, properties) {
  if (isInitialized) {
    posthog.identify(id, properties);
  }
}

export function shutdownPostHog() {
  if (isInitialized) {
    posthog.shutdown();
    isInitialized = false;
  }
}
