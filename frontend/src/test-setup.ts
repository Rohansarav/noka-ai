import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
vi.stubGlobal('scrollTo', vi.fn());
// Allow lazy imports to settle under concurrent CI worker load.
configure({ asyncUtilTimeout: 5000 });
afterEach(cleanup);
