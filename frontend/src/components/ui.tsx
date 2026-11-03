/** Small building blocks shared by the screens, styled with the app's light/dark colors. */
import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';

import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export function Screen({ children }: { children: ReactNode }) {
  const colors = useTheme();
  return <View style={[styles.screen, { backgroundColor: colors.background }]}>{children}</View>;
}

export function Label({ children, muted, size }: { children: ReactNode; muted?: boolean; size?: number }) {
  const colors = useTheme();
  return (
    <Text style={{ color: muted ? colors.textSecondary : colors.text, fontSize: size ?? 16 }}>{children}</Text>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  const colors = useTheme();
  return <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>{children}</Text>;
}

export function Row({ title, detail, onPress }: { title: string; detail?: string; onPress?: () => void }) {
  const colors = useTheme();
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        { backgroundColor: pressed ? colors.backgroundSelected : colors.backgroundElement },
      ]}>
      <Text style={[styles.rowTitle, { color: colors.text }]} numberOfLines={2}>
        {title}
      </Text>
      {detail ? <Text style={{ color: colors.textSecondary }}>{detail}</Text> : null}
      {onPress ? <Text style={{ color: colors.textSecondary }}>›</Text> : null}
    </Pressable>
  );
}

export function Button({
  title,
  onPress,
  primary,
  disabled,
  subtitle,
}: {
  title: string;
  onPress: () => void;
  primary?: boolean;
  disabled?: boolean;
  subtitle?: string;
}) {
  const colors = useTheme();
  const background = primary ? '#208AEF' : colors.backgroundElement;
  const foreground = primary ? '#ffffff' : colors.text;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: background, opacity: disabled ? 0.4 : pressed ? 0.7 : 1 },
      ]}>
      <Text style={[styles.buttonTitle, { color: foreground }]}>{title}</Text>
      {subtitle ? <Text style={{ color: foreground, opacity: 0.8, fontSize: 12 }}>{subtitle}</Text> : null}
    </Pressable>
  );
}

export function Input(props: TextInputProps) {
  const colors = useTheme();
  return (
    <TextInput
      placeholderTextColor={colors.textSecondary}
      {...props}
      style={[styles.input, { color: colors.text, backgroundColor: colors.backgroundElement }, props.style]}
    />
  );
}

export function Loading() {
  return (
    <View style={styles.center}>
      <ActivityIndicator />
    </View>
  );
}

export function ErrorMessage({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View style={[styles.center, { gap: Spacing.three }]}>
      <Text style={styles.error}>{message}</Text>
      {onRetry ? <Button title="Try again" onPress={onRetry} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, padding: Spacing.three, gap: Spacing.two },
  sectionTitle: { fontSize: 13, fontWeight: '600', textTransform: 'uppercase', marginTop: Spacing.three },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingVertical: Spacing.three,
    paddingHorizontal: Spacing.three,
    borderRadius: 10,
  },
  rowTitle: { flex: 1, fontSize: 17 },
  button: { alignItems: 'center', justifyContent: 'center', padding: Spacing.three, borderRadius: 10, flex: 1 },
  buttonTitle: { fontSize: 16, fontWeight: '600' },
  input: { fontSize: 17, padding: Spacing.three, borderRadius: 10 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.four },
  error: { color: '#D93025', fontSize: 16, textAlign: 'center' },
});
