"use client";

import { forwardRef, type ComponentPropsWithoutRef, type ElementType } from "react";
import NextLink from "next/link";
import { clsx } from "clsx";

type ButtonVariant = "primary" | "secondary" | "ghost" | "outline" | "destructive" | "amber";
type ButtonSize = "sm" | "md" | "lg" | "icon";

interface ButtonProps extends ComponentPropsWithoutRef<"button"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const variantClass: Record<ButtonVariant, string> = {
  primary:     "ow-btn-primary",
  secondary:   "ow-btn-secondary",
  ghost:       "ow-btn-ghost",
  outline:     "ow-btn-outline",
  destructive: "ow-btn-destructive",
  amber:       "ow-btn-amber",
};

const sizeClass: Record<ButtonSize, string> = {
  sm:   "ow-btn-sm",
  md:   "ow-btn-md",
  lg:   "ow-btn-lg",
  icon: "ow-btn-icon",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "secondary", size = "md", loading, disabled, children, className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={clsx(
          "ow-btn",
          variantClass[variant],
          sizeClass[size],
          loading && "cursor-wait",
          className
        )}
        {...props}
      >
        {loading ? (
          <>
            <svg
              className="animate-spin"
              width="14" height="14"
              viewBox="0 0 24 24"
              fill="none"
              style={{ flexShrink: 0 }}
            >
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
            {children}
          </>
        ) : children}
      </button>
    );
  }
);

Button.displayName = "Button";

/* Polymorphic link-button (renders <a>) */
interface LinkButtonProps extends ComponentPropsWithoutRef<typeof NextLink> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export function LinkButton({ variant = "secondary", size = "md", className, ...props }: LinkButtonProps) {
  return (
    <NextLink
      className={clsx("ow-btn", variantClass[variant], sizeClass[size], className)}
      {...props}
    />
  );
}
