import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { ScrollView } from 'react-native';

import { Button, Input, Label, Screen, SectionTitle } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { textToHtml } from '@/lib/format';
import { api, ApiError } from '@/services/api';

/** Create a Basic card (front → back) in a topic. */
export default function AddCardScreen() {
  const { topicId } = useLocalSearchParams<{ topicId: string }>();
  const [front, setFront] = useState('');
  const [back, setBack] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const save = async (closeAfter: boolean) => {
    setSaving(true);
    try {
      await api.createNote(Number(topicId), [textToHtml(front), textToHtml(back)]);
      if (closeAfter) {
        router.back();
        return;
      }
      setFront('');
      setBack('');
      setMessage('Saved. Add another one.');
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const ready = front.trim() !== '' && back.trim() !== '' && !saving;

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: Spacing.two }} keyboardShouldPersistTaps="handled">
        <SectionTitle>Front</SectionTitle>
        <Input value={front} onChangeText={setFront} placeholder="Question" multiline autoFocus />
        <SectionTitle>Back</SectionTitle>
        <Input value={back} onChangeText={setBack} placeholder="Answer" multiline />
        <Button primary title="Save" onPress={() => save(true)} disabled={!ready} />
        <Button title="Save and add another" onPress={() => save(false)} disabled={!ready} />
        {message ? <Label muted>{message}</Label> : null}
      </ScrollView>
    </Screen>
  );
}
