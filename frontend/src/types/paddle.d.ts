/* eslint-disable @typescript-eslint/no-explicit-any */

declare namespace Paddle {
  interface CheckoutOptions {
    items: Array<{ priceId: string; quantity: number }>;
    customData?: Record<string, any>;
    settings?: {
      displayMode?: "overlay" | "inline";
      theme?: "light" | "dark";
      locale?: string;
    };
  }

  interface PaddleInstance {
    Initialize(config: { token: string; environment?: string }): void;
    Checkout: {
      open(options: CheckoutOptions): void;
    };
    CustomerPortal: {
      open(): void;
    };
  }
}

interface Window {
  Paddle: Paddle.PaddleInstance;
}
