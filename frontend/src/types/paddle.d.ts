/* eslint-disable @typescript-eslint/no-explicit-any */

declare namespace Paddle {
  interface CheckoutEvent {
    name: string;
    data?: Record<string, unknown>;
    [key: string]: unknown;
  }

  interface CheckoutOptions {
    items: Array<{ priceId: string; quantity: number }>;
    customData?: Record<string, any>;
    settings?: {
      displayMode?: "overlay" | "inline";
      theme?: "light" | "dark";
      locale?: string;
    };
    eventCallback?: (event: CheckoutEvent) => void;
  }

  interface CustomerPortalOptions {
    settings?: {
      displayMode?: "overlay" | "inline";
      theme?: "light" | "dark";
    };
  }

  interface PaddleInstance {
    Initialize(config: { token: string; environment?: string }): void;
    Checkout: {
      open(options: CheckoutOptions): void;
      close(): void;
      updateItems(options: boolean): void;
      updateCheckout(options: boolean): void;
    };
    CustomerPortal: {
      open(options: CustomerPortalOptions): void;
    };
  }
}

interface Window {
  Paddle: Paddle.PaddleInstance;
}
