"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface NumberFieldProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
  suffix?: string;
}

export function NumberField({
  label,
  value,
  onChange,
  step = 1,
  min,
  max,
  suffix,
}: NumberFieldProps) {
  return (
    <div className="space-y-1">
      <Label className="text-sm">
        {label}
        {suffix && (
          <span className="ml-1 text-xs text-muted-foreground">{suffix}</span>
        )}
      </Label>
      <Input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        step={step}
        min={min}
        max={max}
      />
    </div>
  );
}

interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}

export function SelectField({
  label,
  value,
  onChange,
  options,
}: SelectFieldProps) {
  return (
    <div className="space-y-1">
      <Label className="text-sm">{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

interface BoolFieldProps {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}

export function BoolField({ label, value, onChange }: BoolFieldProps) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4"
      />
      <Label className="text-sm">{label}</Label>
    </div>
  );
}

interface ArrayFieldProps {
  label: string;
  value: number[];
  onChange: (v: number[]) => void;
  suffix?: string;
}

export function ArrayField({ label, value, onChange, suffix }: ArrayFieldProps) {
  return (
    <div className="space-y-1">
      <Label className="text-sm">
        {label}
        {suffix && (
          <span className="ml-1 text-xs text-muted-foreground">{suffix}</span>
        )}
      </Label>
      <Input
        type="text"
        value={value.join(", ")}
        onChange={(e) => {
          const parts = e.target.value
            .split(",")
            .map((s) => s.trim())
            .filter((s) => s !== "")
            .map(Number)
            .filter((n) => !isNaN(n));
          onChange(parts.length > 0 ? parts : []);
        }}
        placeholder="e.g. 1000000, 1500000"
      />
    </div>
  );
}
