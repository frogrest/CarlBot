import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Automatically cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.scrollTo
if (typeof window !== 'undefined') {
  window.scrollTo = () => {};
}

// Mock scrollIntoView
Element.prototype.scrollIntoView = () => {};
