import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import { useColorScheme } from 'react-native';

/** All screens are stacked: opening a screen puts it on top, the back button returns. */
export default function RootLayout() {
  const colorScheme = useColorScheme();
  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="index" options={{ title: 'Recall Engine' }} />
        <Stack.Screen name="topic/[id]" options={{ title: '' }} />
        <Stack.Screen name="card/[id]" options={{ title: '' }} />
        <Stack.Screen name="add-card" options={{ title: 'Add card', presentation: 'modal' }} />
        <Stack.Screen name="review" options={{ title: 'Review' }} />
      </Stack>
    </ThemeProvider>
  );
}
