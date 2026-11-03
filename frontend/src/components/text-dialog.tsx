import { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { Button, Input, Label } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/**
 * A small dialog with a text field, e.g. for renaming. React Native has no built-in one on
 * Android (Alert.prompt exists only on iOS), so this is a Modal with an input.
 * Render it only while needed, so each opening starts from `initialValue`.
 */
export function TextDialog({
  title,
  initialValue,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  title: string;
  initialValue: string;
  submitLabel: string;
  /** Resolves when done; throw an Error to show its message and keep the dialog open. */
  onSubmit: (value: string) => Promise<void>;
  onCancel: () => void;
}) {
  const colors = useTheme();
  const [value, setValue] = useState(initialValue);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    try {
      await onSubmit(value.trim());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setSaving(false);
    }
  };

  return (
    <Modal transparent animationType="fade" onRequestClose={onCancel}>
      {/* Tapping the dimmed background cancels */}
      <Pressable style={styles.backdrop} onPress={onCancel}>
        <Pressable style={[styles.dialog, { backgroundColor: colors.background }]} onPress={() => {}}>
          <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
          <Input value={value} onChangeText={setValue} autoFocus selectTextOnFocus onSubmitEditing={submit} />
          {error ? <Label muted>{error}</Label> : null}
          <View style={{ flexDirection: 'row', gap: Spacing.two }}>
            <Button title="Cancel" onPress={onCancel} />
            <Button primary title={submitLabel} onPress={submit} disabled={saving || !value.trim()} />
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    justifyContent: 'center',
    padding: Spacing.four,
  },
  dialog: { borderRadius: 14, padding: Spacing.three, gap: Spacing.three, maxWidth: 480, width: '100%', alignSelf: 'center' },
  title: { fontSize: 18, fontWeight: '600' },
});
